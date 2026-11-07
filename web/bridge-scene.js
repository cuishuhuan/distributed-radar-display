let bridgeInterior, bridgeRadarTexture, coastalObjects=[];
function headingRibbon(angle){
  const heading=((angle%360)+360)%360;
  const side=offset=>{const value=(heading+offset+360)%360;return `<span class="heading-neighbor"><b>${compassText(value)}</b><small>${Math.round(value)%360}°</small></span>`};
  return `${side(-45)}<span class="heading-center"><b>${Math.round(heading)%360}°</b><small>${compassText(heading)}方位</small></span>${side(45)}`;
}
let bridgeReadouts=[],bridgeReadoutTime=0;
function bridgeInstrumentTexture(title){
  const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=600;
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
  bridgeReadouts.push({canvas,texture,title});return texture;
}
function updateBridgeReadouts(own){
  if(performance.now()-bridgeReadoutTime<400)return;bridgeReadoutTime=performance.now();
  const ship=typeof viewShip!=='undefined'&&viewShip?viewShip:{name:'本船',speed:0};
  for(const {canvas,texture,title} of bridgeReadouts){
    const c=canvas.getContext('2d');c.fillStyle='#061117';c.fillRect(0,0,1024,600);
    c.fillStyle='#112c35';c.fillRect(0,0,1024,62);c.fillStyle='#a0c9cb';c.font='26px Microsoft YaHei';c.fillText(title,32,42);
    c.fillStyle='#6acdb1';c.font='20px Microsoft YaHei';c.fillText('● 航行数据',805,40);
    if(title==='电子航行显示'){
      c.strokeStyle='#183d48';c.lineWidth=1;for(let x=20;x<1024;x+=60){c.beginPath();c.moveTo(x,75);c.lineTo(x,600);c.stroke()}for(let y=90;y<600;y+=60){c.beginPath();c.moveTo(0,y);c.lineTo(1024,y);c.stroke()}
      c.strokeStyle='#507c7d';c.lineWidth=3;c.beginPath();c.moveTo(40,570);c.bezierCurveTo(240,480,80,320,250,230);c.bezierCurveTo(330,160,480,210,550,90);c.stroke();
      c.strokeStyle='#b8ad61';c.setLineDash([14,10]);c.beginPath();c.moveTo(505,560);c.lineTo(560,350);c.lineTo(720,110);c.stroke();c.setLineDash([]);
      c.fillStyle='#9de2c7';c.beginPath();c.moveTo(555,285);c.lineTo(579,355);c.lineTo(555,342);c.lineTo(531,355);c.fill();
      c.fillStyle='#1b333a';c.fillRect(730,80,280,480);c.fillStyle='#bbd6d3';c.font='22px Microsoft YaHei';c.fillText('本船状态',755,120);c.font='22px monospace';c.fillText(ship.speed.toFixed(1)+' kn',755,180);c.fillText(Math.round(own.course||0)+'°',755,235);c.fillStyle='#6f949a';c.font='20px Microsoft YaHei';c.fillText('航迹显示 · 示意',755,520);
    }else{
      c.fillStyle='#7d9a9f';c.font='25px Microsoft YaHei';c.fillText('当前航向',45,125);c.fillText('对地航速',535,125);
      c.fillStyle='#d1e8df';c.font='100px monospace';c.fillText(String(Math.round(own.course||0)).padStart(3,'0')+'°',40,245);c.fillText(ship.speed.toFixed(1),530,245);c.font='24px monospace';c.fillText('kn',850,245);
      c.strokeStyle='#2e505a';c.lineWidth=2;c.strokeRect(35,300,950,235);c.fillStyle='#7a9b9d';c.font='23px Microsoft YaHei';c.fillText('航向保持',60,345);c.fillText('船舶识别',60,410);c.fillText('雷达链路',530,410);c.fillStyle='#89c7ad';c.fillText('航行监测',530,345);c.fillText(ship.name,60,490);
    }texture.needsUpdate=true;
  }
}
function installBridgeInterior(){
  if(bridgeInterior)return;
  const g=bridgeInterior=new THREE.Group();g.position.set(0,6.4,8.7);fpScene.add(g);
  const material=(color,metalness=0,roughness=.75)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
  const cabinet=material(0x0c141b,.18),rubber=material(0x05090c),frame=material(0x263239,.45,.48),metal=material(0x53646a,.6,.4),wall=material(0x475259),floor=material(0x182127);
  const panel=(w,h,d,x,y,z,mat=cabinet,r=.04,parent=g)=>{
    const shape=new THREE.Shape(),a=-w/2,b=-h/2;
    shape.moveTo(a+r,b);shape.lineTo(a+w-r,b);shape.quadraticCurveTo(a+w,b,a+w,b+r);shape.lineTo(a+w,b+h-r);shape.quadraticCurveTo(a+w,b+h,a+w-r,b+h);shape.lineTo(a+r,b+h);shape.quadraticCurveTo(a,b+h,a,b+h-r);shape.lineTo(a,b+r);shape.quadraticCurveTo(a,b,a+r,b);
    const mesh=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:d,bevelEnabled:true,bevelSize:.012,bevelThickness:.012,bevelSegments:3,curveSegments:6,steps:1}),mat);mesh.position.set(x,y,z-d/2);parent.add(mesh);return mesh;
  };
  const box=(w,h,d,x,y,z,mat=cabinet,parent=g)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y,z);parent.add(m);return m};
  const cylinder=(radius,length,x,y,z,mat=metal,parent=g)=>{const m=new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,length,24),mat);m.rotation.x=Math.PI/2;m.position.set(x,y,z);parent.add(m);return m};
  box(14,.15,10,0,-1.95,.4,floor);box(14,.15,10,0,2.65,.4,wall);box(14,4.6,.15,0,.3,5.2,wall);
  for(const x of [-6.9,6.9])box(.18,4.6,10,x,.3,.4,wall);
  // Narrow dark mullions keep the horizon visible from the seated eye point.
  for(const x of [-6.5,-2.6,2.6,6.5]){const post=box(.075,3.5,.14,x,1,-4.45,frame);post.rotation.x=-.1}
  box(13.1,.1,.18,0,-.71,-4.45,frame);box(13.1,.14,.18,0,2.65,-4.78,frame);
  for(const x of [-6.5,6.5]){box(.08,3.5,.12,x,1,1.8,frame);box(.1,.1,6,x,-.71,-1.4,frame)}
  for(const x of [-3.7,3.7]){panel(1.6,.06,.15,x,2.5,-1.3,rubber,.025);const strip=box(1.35,.012,.045,x,2.45,-1.28,new THREE.MeshBasicMaterial({color:0xa4c7c0}));}
  const screen=(x,texture)=>{
    const group=new THREE.Group();group.position.set(x,-.75,-3.65);group.rotation.x=-.25;g.add(group);
    panel(1.92,1.19,.14,0,0,0,rubber,.065,group);panel(1.77,1.04,.025,0,.025,.085,frame,.035,group);
    const face=new THREE.Mesh(new THREE.PlaneGeometry(1.65,.96),new THREE.MeshBasicMaterial({map:texture,toneMapped:false}));face.position.set(0,.025,.135);group.add(face);
    for(const sx of [-.86,.86])for(const sy of [-.51,.51])cylinder(.014,.008,sx,sy,.085,metal,group);
    cylinder(.032,.02,.76,-.53,.1,metal,group);
  };
  const radar=document.getElementById('miniRadar');bridgeRadarTexture=new THREE.CanvasTexture(radar);bridgeRadarTexture.colorSpace=THREE.SRGBColorSpace;
  for(const [index,x] of [-2.1,0,2.1].entries()){
    panel(2.08,.78,1.15,x,-1.49,-3.27,cabinet,.06);panel(2.13,.12,1.4,x,-1.1,-3.16,rubber,.035);
    screen(x,index===0?bridgeRadarTexture:bridgeInstrumentTexture(index===1?'电子航行显示':'综合航行仪表'));
    for(let i=0;i<7;i++)box(.75,.012,.015,x,-1.28-i*.045,-2.68,frame);
    panel(1.8,.12,.025,x,-1.15,-2.65,frame,.015);
    for(let i=0;i<5;i++)cylinder(.025,.025,x-.5+i*.25,-1.15,-2.62,i===0?material(0x2a6c54):rubber);
  }
  panel(1.25,.18,.72,-.4,-1.48,-2.1,rubber,.08);
  const steering=new THREE.Group();steering.position.set(-.4,-1.35,-2.15);steering.rotation.x=-.22;g.add(steering);
  const rim=new THREE.Mesh(new THREE.TorusGeometry(.255,.027,16,64),rubber);steering.add(rim);cylinder(.07,.06,0,0,0,frame,steering);
  for(let i=0;i<3;i++){const spoke=box(.022,.22,.026,0,-.12,0,metal,steering);spoke.position.set(Math.sin(i*Math.PI*2/3)*.12,-Math.cos(i*Math.PI*2/3)*.12,0);spoke.rotation.z=i*Math.PI*2/3}
  const throttle=new THREE.Group();throttle.position.set(2.8,-1.25,-2.25);g.add(throttle);panel(.62,.18,.8,0,-.12,0,frame,.07,throttle);
  for(const x of [-.14,.14]){box(.035,.025,.5,x,0,0,rubber,throttle);const lever=box(.025,.31,.025,x,.13,-.03,metal,throttle);lever.rotation.x=-.3;panel(.15,.08,.11,x,.29,-.08,rubber,.035,throttle)}
  for(const x of [-4.5,4.5]){
    panel(1.2,.16,1.5,x,-1.15,-2.4,cabinet,.07);panel(.65,.55,.1,x,-.78,-2.75,rubber,.05);
    for(let row=0;row<3;row++)for(let col=0;col<4;col++)panel(.07,.04,.018,x-.22+col*.14,-.66-row*.1,-2.69,frame,.008);
  }
  for(const x of [-1.8,1.8]){cylinder(.11,1,x,-1.4,1.5,metal);panel(.75,.16,.8,x,-.95,1.5,rubber,.1);panel(.75,.95,.14,x,-.45,1.85,rubber,.1);for(const dx of [-.47,.47])panel(.12,.12,.6,x+dx,-.63,1.5,frame,.05)}
  updateBridgeReadouts({course:0});
}
function updateCoastalScene(own,heading){
  if(!coastalObjects.length){
    const sites=[{lon:113.588,lat:22.46,city:true},{lon:113.602,lat:22.59,city:true},{lon:113.835,lat:22.55,city:true},{lon:113.872,lat:22.45},{lon:113.69,lat:22.34},{lon:113.55,lat:22.38}];
    coastalObjects=sites.map((geo,index)=>{
      const group=new THREE.Group();group.userData.geo=geo;fpScene.add(group);
      const landMat=new THREE.MeshStandardMaterial({color:0x426c5b,roughness:1});
      for(let i=0;i<7;i++){const hill=new THREE.Mesh(new THREE.SphereGeometry(1,24,14),landMat);const h=7+(i*7+index*3)%18;hill.scale.set(22,h,17);hill.position.set((i-3)*25,h*.12-5,Math.sin(i*1.7)*13);group.add(hill)}
      if(geo.city){const quay=new THREE.Mesh(new THREE.BoxGeometry(110,2,12),new THREE.MeshStandardMaterial({color:0x7d8583}));quay.position.set(0,0,22);group.add(quay);for(let i=0;i<16;i++){const height=4+(i*11+index*7)%25;const building=new THREE.Mesh(new THREE.BoxGeometry(4+i%3,height,5),new THREE.MeshStandardMaterial({color:i%3?0x98adb5:0xb8b8a8,roughness:.8}));building.position.set((i-7.5)*6,height/2,6+(i%3)*5);group.add(building);for(let floor=3;floor<height;floor+=3){const windows=new THREE.Mesh(new THREE.BoxGeometry(3,.5,.03),new THREE.MeshStandardMaterial({color:0x426878,emissive:0x142a30}));windows.position.set(building.position.x,floor,building.position.z+2.52);group.add(windows)}}for(let i=0;i<3;i++){const mat=new THREE.MeshStandardMaterial({color:0xa28c62,metalness:.4,roughness:.6});const column=new THREE.Mesh(new THREE.BoxGeometry(.7,15,.7),mat);column.position.set(-30+i*25,8,27);group.add(column);const arm=new THREE.Mesh(new THREE.BoxGeometry(.7,.7,20),mat);arm.position.set(-30+i*25,15,32);group.add(arm)}}
      return group;
    });
  }
  for(const object of coastalObjects){const geo=object.userData.geo,dx=(geo.lon-own.lon)*111.32*Math.cos(own.lat*Math.PI/180),dy=(geo.lat-own.lat)*110.57;object.position.set((dx*Math.cos(heading)-dy*Math.sin(heading))*WORLD_KM,-.5,-(dx*Math.sin(heading)+dy*Math.cos(heading))*WORLD_KM);object.rotation.y=heading;}
  if(bridgeRadarTexture&&fpFrame%10===0)bridgeRadarTexture.needsUpdate=true;
  updateBridgeReadouts(own);
}
