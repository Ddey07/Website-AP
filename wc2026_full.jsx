import { useState, useEffect } from "react";

// ── OFFICIAL FIFA POINTS — 01 April 2026 ─────────────────────────────────────
const ELO = {
  France:1877,Spain:1876,Argentina:1875,England:1826,
  Portugal:1764,Brazil:1761,Netherlands:1758,Morocco:1757,
  Belgium:1735,Germany:1730,Croatia:1717,Colombia:1693,
  Senegal:1692,Mexico:1680,USA:1665,Uruguay:1650,
  Japan:1637,Switzerland:1625,Iran:1598,Turkey:1585,
  Ecuador:1572,Austria:1558,"South Korea":1545,Australia:1519,
  Algeria:1506,Egypt:1492,Canada:1479,Norway:1466,
  Panama:1440,"Ivory Coast":1427,Sweden:1388,Paraguay:1362,
  Czechia:1348,Scotland:1320,Tunisia:1307,"DR Congo":1280,
  Uzbekistan:1236,Qatar:1188,Iraq:1174,"South Africa":1153,
  "Saudi Arabia":1145,Jordan:1131,"Bosnia-Herz.":1117,
  "Cape Verde":1090,Ghana:1058,Curacao:1010,Haiti:1005,"New Zealand":995,
};
const FORM = {
  France:+7.32,Spain:-0.78,Argentina:+1.49,England:-8.15,
  Portugal:+3.45,Brazil:+0.70,Netherlands:+1.60,Morocco:+20.23,
  Belgium:+4.01,Germany:+6.22,Croatia:+0.18,Colombia:-8.21,
  Senegal:-14.86,Mexico:+2.0,USA:-12.0,Uruguay:+1.0,
  Japan:+5.0,Switzerland:+1.0,Iran:-2.0,Turkey:+3.0,
  Ecuador:-1.0,Austria:+1.0,"South Korea":-1.0,Australia:+1.0,
  Algeria:+2.0,Egypt:+1.0,Canada:-3.0,Norway:+1.0,
  "Ivory Coast":+3.0,Sweden:+2.0,Paraguay:+1.0,Panama:-1.0,
  Czechia:+1.0,Scotland:-3.0,Tunisia:0,"DR Congo":-1.0,
  Uzbekistan:+1.0,Qatar:-1.0,Iraq:+1.0,"South Africa":0,
  "Saudi Arabia":-1.0,Jordan:0,"Bosnia-Herz.":+2.0,
  "Cape Verde":+1.0,Ghana:0,Curacao:0,Haiti:+1.0,"New Zealand":0,
};
const FLAGS = {
  France:"🇫🇷",Spain:"🇪🇸",Argentina:"🇦🇷",England:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",Portugal:"🇵🇹",
  Brazil:"🇧🇷",Netherlands:"🇳🇱",Morocco:"🇲🇦",Belgium:"🇧🇪",Germany:"🇩🇪",
  Croatia:"🇭🇷",Colombia:"🇨🇴",Senegal:"🇸🇳",Mexico:"🇲🇽",USA:"🇺🇸",
  Uruguay:"🇺🇾",Japan:"🇯🇵",Switzerland:"🇨🇭",Iran:"🇮🇷",Turkey:"🇹🇷",
  Ecuador:"🇪🇨",Austria:"🇦🇹","South Korea":"🇰🇷",Australia:"🇦🇺",
  Algeria:"🇩🇿",Egypt:"🇪🇬",Canada:"🇨🇦",Norway:"🇳🇴",Panama:"🇵🇦",
  "Ivory Coast":"🇨🇮",Sweden:"🇸🇪",Paraguay:"🇵🇾",Czechia:"🇨🇿",
  Scotland:"🏴󠁧󠁢󠁳󠁣󠁴󠁿",Tunisia:"🇹🇳","DR Congo":"🇨🇩",Uzbekistan:"🇺🇿",
  Qatar:"🇶🇦",Iraq:"🇮🇶","South Africa":"🇿🇦","Saudi Arabia":"🇸🇦",
  Jordan:"🇯🇴","Bosnia-Herz.":"🇧🇦","Cape Verde":"🇨🇻",Ghana:"🇬🇭",
  Curacao:"🇨🇼",Haiti:"🇭🇹","New Zealand":"🇳🇿",
};
const COLORS = {
  France:"#1565C0",Spain:"#C62828",Argentina:"#0277BD",England:"#1B5E20",
  Portugal:"#880E4F",Brazil:"#F9A825",Netherlands:"#E65100",Morocco:"#2E7D32",
  Belgium:"#4E342E",Germany:"#546E7A",Croatia:"#B71C1C",Colombia:"#F57F17",
  Senegal:"#006400",Mexico:"#1B5E20",USA:"#9B1C1C",Uruguay:"#1A237E",
};

const SORTED_ELO = Object.entries(ELO).sort(([,a],[,b])=>b-a);
const RANKS = SORTED_ELO.reduce((acc,[t],i)=>{acc[t]=i+1;return acc;},{});

function fl(t){return FLAGS[t]||"⚽";}
function e(t){return ELO[t]||1200;}
function wp(a,b){return 1/(1+Math.pow(10,(e(b)-e(a))/400));}
function simMatch(a,b){return Math.random()<wp(a,b)?a:b;}
function fc(f){
  if(f>10)return"#4ade80"; if(f>3)return"#86efac";
  if(f>0)return"#bef264"; if(f>-3)return"#94a3b8";
  if(f>-10)return"#fca5a5"; return"#f87171";
}
function fa(f){return f>=5?"↑↑":f>=1?"↑":f>-1?"→":f>=-5?"↓":"↓↓";}

// ── GROUPS ────────────────────────────────────────────────────────────────────
const GROUPS = {
  A:{teams:["Mexico","South Africa","South Korea","Czechia"],proj:["Mexico","South Korea"]},
  B:{teams:["Canada","Bosnia-Herz.","Qatar","Switzerland"],proj:["Switzerland","Canada"]},
  C:{teams:["Brazil","Morocco","Haiti","Scotland"],proj:["Brazil","Morocco"]},
  D:{teams:["USA","Paraguay","Australia","Turkey"],proj:["USA","Turkey"]},
  E:{teams:["Germany","Curacao","Ivory Coast","Ecuador"],proj:["Germany","Ecuador"]},
  F:{teams:["Netherlands","Japan","Sweden","Tunisia"],proj:["Netherlands","Japan"]},
  G:{teams:["Belgium","Egypt","Iran","New Zealand"],proj:["Belgium","Iran"]},
  H:{teams:["Spain","Cape Verde","Saudi Arabia","Uruguay"],proj:["Spain","Uruguay"]},
  I:{teams:["France","Senegal","Iraq","Norway"],proj:["France","Senegal"]},
  J:{teams:["Argentina","Algeria","Austria","Jordan"],proj:["Argentina","Austria"]},
  K:{teams:["Portugal","DR Congo","Uzbekistan","Colombia"],proj:["Portugal","Colombia"]},
  L:{teams:["England","Croatia","Ghana","Panama"],proj:["England","Croatia"]},
};

// ── GROUP STAGE SCHEDULE ──────────────────────────────────────────────────────
const GS = {
  A:[
    {date:"Jun 11",a:"Mexico",b:"South Africa",venue:"Mexico City (Azteca)"},
    {date:"Jun 11",a:"South Korea",b:"Czechia",venue:"Guadalupe (Akron, MEX)"},
    {date:"Jun 18",a:"Czechia",b:"South Africa",venue:"Atlanta (Mercedes-Benz)"},
    {date:"Jun 18",a:"Mexico",b:"South Korea",venue:"Guadalupe (Akron, MEX)"},
    {date:"Jun 24",a:"South Africa",b:"South Korea",venue:"Atlanta (Mercedes-Benz)"},
    {date:"Jun 24",a:"Czechia",b:"Mexico",venue:"Mexico City (Azteca)"},
  ],
  B:[
    {date:"Jun 12",a:"Canada",b:"Bosnia-Herz.",venue:"Toronto (BMO Field)"},
    {date:"Jun 13",a:"Qatar",b:"Switzerland",venue:"Santa Clara (Levi's)"},
    {date:"Jun 18",a:"Switzerland",b:"Bosnia-Herz.",venue:"Inglewood (SoFi)"},
    {date:"Jun 18",a:"Canada",b:"Qatar",venue:"Vancouver (BC Place)"},
    {date:"Jun 23",a:"Bosnia-Herz.",b:"Qatar",venue:"Vancouver (BC Place)"},
    {date:"Jun 23",a:"Switzerland",b:"Canada",venue:"Seattle (Lumen Field)"},
  ],
  C:[
    {date:"Jun 13",a:"Brazil",b:"Morocco",venue:"E.Rutherford (MetLife)"},
    {date:"Jun 13",a:"Haiti",b:"Scotland",venue:"Foxborough (Gillette)"},
    {date:"Jun 19",a:"Scotland",b:"Morocco",venue:"Boston (Gillette)"},
    {date:"Jun 19",a:"Brazil",b:"Haiti",venue:"Kansas City (Arrowhead)"},
    {date:"Jun 24",a:"Haiti",b:"Morocco",venue:"Miami (Hard Rock)"},
    {date:"Jun 24",a:"Scotland",b:"Brazil",venue:"Philadelphia (Lincoln Fin.)"},
  ],
  D:[
    {date:"Jun 12",a:"USA",b:"Paraguay",venue:"Inglewood (SoFi)"},
    {date:"Jun 14",a:"Australia",b:"Turkey",venue:"Kansas City (Arrowhead)"},
    {date:"Jun 19",a:"USA",b:"Australia",venue:"Seattle (Lumen Field)"},
    {date:"Jun 19",a:"Turkey",b:"Paraguay",venue:"Santa Clara (Levi's)"},
    {date:"Jun 25",a:"Australia",b:"Paraguay",venue:"Miami (Hard Rock)"},
    {date:"Jun 25",a:"USA",b:"Turkey",venue:"Inglewood (SoFi)"},
  ],
  E:[
    {date:"Jun 14",a:"Germany",b:"Ivory Coast",venue:"Toronto (BMO Field)"},
    {date:"Jun 14",a:"Ecuador",b:"Curacao",venue:"Kansas City (Arrowhead)"},
    {date:"Jun 19",a:"Ivory Coast",b:"Curacao",venue:"Philadelphia (Lincoln Fin.)"},
    {date:"Jun 20",a:"Germany",b:"Ecuador",venue:"Vancouver (BC Place)"},
    {date:"Jun 25",a:"Curacao",b:"Germany",venue:"Atlanta (Mercedes-Benz)"},
    {date:"Jun 25",a:"Ivory Coast",b:"Ecuador",venue:"Toronto (BMO Field)"},
  ],
  F:[
    {date:"Jun 14",a:"Netherlands",b:"Japan",venue:"Philadelphia (Lincoln Fin.)"},
    {date:"Jun 14",a:"Sweden",b:"Tunisia",venue:"Monterrey (Estadio BBVA, MEX)"},
    {date:"Jun 21",a:"Netherlands",b:"Sweden",venue:"Houston (NRG) 🤠",texas:true},
    {date:"Jun 21",a:"Tunisia",b:"Japan",venue:"Monterrey (Estadio BBVA, MEX)"},
    {date:"Jun 26",a:"Japan",b:"Sweden",venue:"Boston (Gillette)"},
    {date:"Jun 26",a:"Tunisia",b:"Netherlands",venue:"Atlanta (Mercedes-Benz)"},
  ],
  G:[
    {date:"Jun 15",a:"Belgium",b:"Egypt",venue:"Seattle (Lumen Field)"},
    {date:"Jun 15",a:"Iran",b:"New Zealand",venue:"Inglewood (SoFi)"},
    {date:"Jun 21",a:"Belgium",b:"Iran",venue:"Inglewood (SoFi)"},
    {date:"Jun 21",a:"New Zealand",b:"Egypt",venue:"Vancouver (BC Place)"},
    {date:"Jun 26",a:"Egypt",b:"Iran",venue:"Kansas City (Arrowhead)"},
    {date:"Jun 26",a:"New Zealand",b:"Belgium",venue:"Santa Clara (Levi's)"},
  ],
  H:[
    {date:"Jun 15",a:"Spain",b:"Cape Verde",venue:"Atlanta (Mercedes-Benz)"},
    {date:"Jun 15",a:"Saudi Arabia",b:"Uruguay",venue:"Miami (Hard Rock)"},
    {date:"Jun 21",a:"Spain",b:"Saudi Arabia",venue:"Atlanta (Mercedes-Benz)"},
    {date:"Jun 21",a:"Uruguay",b:"Cape Verde",venue:"Miami (Hard Rock)"},
    {date:"Jun 26",a:"Cape Verde",b:"Saudi Arabia",venue:"Miami (Hard Rock)"},
    {date:"Jun 26",a:"Uruguay",b:"Spain",venue:"Guadalupe (Akron, MEX)"},
  ],
  I:[
    {date:"Jun 16",a:"France",b:"Senegal",venue:"E.Rutherford (MetLife)"},
    {date:"Jun 16",a:"Iraq",b:"Norway",venue:"Foxborough (Gillette)"},
    {date:"Jun 22",a:"France",b:"Iraq",venue:"Philadelphia (Lincoln Fin.)"},
    {date:"Jun 22",a:"Norway",b:"Senegal",venue:"Seattle (Lumen Field)"},
    {date:"Jun 26",a:"Senegal",b:"Iraq",venue:"Seattle (Lumen Field)"},
    {date:"Jun 26",a:"Norway",b:"France",venue:"Vancouver (BC Place)"},
  ],
  J:[
    {date:"Jun 16",a:"Argentina",b:"Algeria",venue:"Kansas City (Arrowhead)"},
    {date:"Jun 16",a:"Austria",b:"Jordan",venue:"Santa Clara (Levi's)"},
    {date:"Jun 22",a:"Argentina",b:"Austria",venue:"Dallas (AT&T) 🤠",texas:true},
    {date:"Jun 22",a:"Jordan",b:"Algeria",venue:"Seattle (Lumen Field)"},
    {date:"Jun 27",a:"Algeria",b:"Austria",venue:"Miami (Hard Rock)"},
    {date:"Jun 27",a:"Jordan",b:"Argentina",venue:"Dallas (AT&T) 🤠",texas:true},
  ],
  K:[
    {date:"Jun 17",a:"Portugal",b:"DR Congo",venue:"Houston (NRG) 🤠",texas:true},
    {date:"Jun 17",a:"Uzbekistan",b:"Colombia",venue:"Mexico City (Azteca)"},
    {date:"Jun 23",a:"Portugal",b:"Uzbekistan",venue:"Kansas City (Arrowhead)"},
    {date:"Jun 23",a:"Colombia",b:"DR Congo",venue:"Philadelphia (Lincoln Fin.)"},
    {date:"Jun 27",a:"DR Congo",b:"Uzbekistan",venue:"Boston (Gillette)"},
    {date:"Jun 27",a:"Colombia",b:"Portugal",venue:"Miami (Hard Rock)"},
  ],
  L:[
    {date:"Jun 17",a:"England",b:"Croatia",venue:"Dallas (AT&T) 🤠",texas:true},
    {date:"Jun 17",a:"Ghana",b:"Panama",venue:"Toronto (BMO Field)"},
    {date:"Jun 23",a:"England",b:"Ghana",venue:"Philadelphia (Lincoln Fin.)"},
    {date:"Jun 23",a:"Panama",b:"Croatia",venue:"Vancouver (BC Place)"},
    {date:"Jun 27",a:"Croatia",b:"Ghana",venue:"Atlanta (Mercedes-Benz)"},
    {date:"Jun 27",a:"Panama",b:"England",venue:"Santa Clara (Levi's)"},
  ],
};

// ── KNOCKOUT SLOT DEFINITIONS (official bracket) ──────────────────────────────
// Order within each round matches the simulation array indices
const KO = {
  r32:[
    // → R16 M89 (Philly) → QF M97 (Boston) → SF M101 (Dallas ★)
    {m:"M74",date:"Jun 29",venue:"Foxborough (Gillette)",desc:"W-E vs 3rd A/B/C/D/F"},
    {m:"M77",date:"Jun 30",venue:"E.Rutherford (MetLife)",desc:"W-I vs 3rd C/D/F/G/H"},
    // → R16 M90 (Houston ★) → QF M97 (Boston) → SF M101 (Dallas ★)
    {m:"M73",date:"Jun 28",venue:"Inglewood (SoFi)",desc:"RU-A vs RU-B"},
    {m:"M75",date:"Jun 29",venue:"Guadalupe (BBVA, MEX)",desc:"W-F vs RU-C"},
    // → R16 M93 (Dallas ★) → QF M98 (Inglewood) → SF M101 (Dallas ★)
    {m:"M83",date:"Jul 2",venue:"Toronto (BMO Field)",desc:"RU-K vs RU-L"},
    {m:"M84",date:"Jul 2",venue:"Inglewood (SoFi)",desc:"W-H vs RU-J"},
    // → R16 M94 (Seattle) → QF M98 (Inglewood) → SF M101 (Dallas ★)
    {m:"M81",date:"Jul 1",venue:"Santa Clara (Levi's)",desc:"W-D vs 3rd B/E/F/I/J"},
    {m:"M82",date:"Jul 1",venue:"Seattle (Lumen Field)",desc:"W-G vs 3rd A/E/H/I/J"},
    // → R16 M91 (E.Rutherford) → QF M99 (Miami) → SF M102 (Atlanta)
    {m:"M76",date:"Jun 29",venue:"Houston (NRG) 🤠",desc:"W-C vs RU-F",texas:true},
    {m:"M78",date:"Jun 30",venue:"Dallas (AT&T) 🤠",desc:"RU-E vs RU-I",texas:true},
    // → R16 M92 (Mexico City) → QF M99 (Miami) → SF M102 (Atlanta)
    {m:"M79",date:"Jun 30",venue:"Mexico City (Azteca)",desc:"W-A vs 3rd C/E/F/H/I"},
    {m:"M80",date:"Jul 1",venue:"Atlanta (Mercedes-Benz)",desc:"W-L vs 3rd E/H/I/J/K"},
    // → R16 M95 (Atlanta) → QF M100 (Kansas City) → SF M102 (Atlanta)
    {m:"M86",date:"Jul 3",venue:"Atlanta (Mercedes-Benz)",desc:"W-J vs RU-H"},
    {m:"M88",date:"Jul 3",venue:"Dallas (AT&T) 🤠",desc:"RU-D vs RU-G",texas:true},
    // → R16 M96 (Vancouver) → QF M100 (Kansas City) → SF M102 (Atlanta)
    {m:"M85",date:"Jul 2",venue:"Vancouver (BC Place)",desc:"W-B vs 3rd E/F/G/I/J"},
    {m:"M87",date:"Jul 3",venue:"Kansas City (Arrowhead)",desc:"W-K vs 3rd D/E/I/J/L"},
  ],
  r16:[
    {m:"M89",date:"Jul 4",venue:"Philadelphia (Lincoln Fin.)",desc:"W(M74) vs W(M77) → QF Boston"},
    {m:"M90",date:"Jul 4",venue:"Houston (NRG) 🤠",desc:"W(M73) vs W(M75) → QF Boston",texas:true},
    {m:"M93",date:"Jul 6",venue:"Dallas (AT&T) 🤠",desc:"W(M83) vs W(M84) → QF Inglewood",texas:true},
    {m:"M94",date:"Jul 6",venue:"Seattle (Lumen Field)",desc:"W(M81) vs W(M82) → QF Inglewood"},
    {m:"M91",date:"Jul 5",venue:"E.Rutherford (MetLife)",desc:"W(M76) vs W(M78) → QF Miami"},
    {m:"M92",date:"Jul 5",venue:"Mexico City (Azteca)",desc:"W(M79) vs W(M80) → QF Miami"},
    {m:"M95",date:"Jul 7",venue:"Atlanta (Mercedes-Benz)",desc:"W(M86) vs W(M88) → QF KC"},
    {m:"M96",date:"Jul 7",venue:"Vancouver (BC Place)",desc:"W(M85) vs W(M87) → QF KC"},
  ],
  qf:[
    {m:"M97",date:"Jul 9", venue:"Boston (Gillette)",desc:"W(M89) vs W(M90) → SF Dallas"},
    {m:"M98",date:"Jul 10",venue:"Inglewood (SoFi)",desc:"W(M93) vs W(M94) → SF Dallas"},
    {m:"M99",date:"Jul 11",venue:"Miami (Hard Rock)",desc:"W(M91) vs W(M92) → SF Atlanta"},
    {m:"M100",date:"Jul 11",venue:"Kansas City (Arrowhead)",desc:"W(M95) vs W(M96) → SF Atlanta"},
  ],
  sf:[
    {m:"M101",date:"Jul 14",venue:"Dallas AT&T ⭐",desc:"W(M97) vs W(M98)",texas:true},
    {m:"M102",date:"Jul 15",venue:"Atlanta (Mercedes-Benz)",desc:"W(M99) vs W(M100)"},
  ],
  final:[
    {m:"M103",date:"Jul 19",venue:"E.Rutherford (MetLife)",desc:"W(M101) vs W(M102)"},
  ],
};

// ── SIMULATION ────────────────────────────────────────────────────────────────
const SLOT_ALLOW = {
  M74:["A","B","C","D","F"],M77:["C","D","F","G","H"],
  M79:["C","E","F","H","I"],M80:["E","H","I","J","K"],
  M81:["B","E","F","I","J"],M82:["A","E","H","I","J"],
  M85:["E","F","G","I","J"],M87:["D","E","I","J","L"],
};

function simGroup(teams){
  const pts={},gd={};
  teams.forEach(t=>{pts[t]=0;gd[t]=0;});
  for(let i=0;i<teams.length;i++){
    for(let j=i+1;j<teams.length;j++){
      const a=teams[i],b=teams[j],pA=wp(a,b)*0.75,r=Math.random();
      if(r<pA){pts[a]+=3;gd[a]+=(1+Math.random());gd[b]-=Math.random();}
      else if(r<pA+0.25){pts[a]+=1;pts[b]+=1;}
      else{pts[b]+=3;gd[b]+=(1+Math.random());gd[a]-=Math.random();}
    }
  }
  return [...teams].sort((a,b)=>pts[b]-pts[a]||gd[b]-gd[a]||Math.random()-.5);
}

function assign3rd(thirds){
  const slots=Object.keys(SLOT_ALLOW),res={},used=new Set();
  let changed=true;
  while(changed){
    changed=false;
    for(const s of slots){
      if(res[s])continue;
      const v=thirds.filter(t=>!used.has(t.team)&&SLOT_ALLOW[s].includes(t.group));
      if(v.length===1){res[s]=v[0].team;used.add(v[0].team);changed=true;}
    }
  }
  for(const s of slots){
    if(res[s])continue;
    const v=thirds.filter(t=>!used.has(t.team)&&SLOT_ALLOW[s].includes(t.group));
    if(v.length>0){res[s]=v[0].team;used.add(v[0].team);}
    else res[s]="TBD";
  }
  return res;
}

function runOnce(){
  const W={},R={},thirds=[];
  for(const[g,{teams}]of Object.entries(GROUPS)){
    const rk=simGroup(teams);
    W[g]=rk[0];R[g]=rk[1];
    thirds.push({team:rk[2],group:g,pts:e(rk[2])});
  }
  thirds.sort((a,b)=>b.pts-a.pts);
  const sg=assign3rd(thirds);
  const gv=k=>sg[k]||"TBD";
  const ok=(a,b)=>a&&b&&a!=="TBD"&&b!=="TBD"&&a!==b;
  const key=(a,b)=>[a,b].sort().join("|");

  // 16 R32 pairs — index must match KO.r32 order
  const r32p=[
    [W.E,gv("M74")],[W.I,gv("M77")],[R.A,R.B],[W.F,R.C],
    [R.K,R.L],[W.H,R.J],[W.D,gv("M81")],[W.G,gv("M82")],
    [W.C,R.F],[R.E,R.I],[W.A,gv("M79")],[W.L,gv("M80")],
    [W.J,R.H],[R.D,R.G],[W.B,gv("M85")],[W.K,gv("M87")],
  ];

  const out={r32:[],r16:[],qf:[],sf:[],final:[]};

  const r32w=r32p.map(([a,b],idx)=>{
    if(!ok(a,b))return a&&a!=="TBD"?a:b&&b!=="TBD"?b:"TBD";
    out.r32.push({idx,key:key(a,b)});
    return simMatch(a,b);
  });

  const r16p=[[r32w[0],r32w[1]],[r32w[2],r32w[3]],[r32w[4],r32w[5]],[r32w[6],r32w[7]],
              [r32w[8],r32w[9]],[r32w[10],r32w[11]],[r32w[12],r32w[13]],[r32w[14],r32w[15]]];
  const r16w=r16p.map(([a,b],idx)=>{
    if(!ok(a,b))return a&&a!=="TBD"?a:b&&b!=="TBD"?b:"TBD";
    out.r16.push({idx,key:key(a,b)});
    return simMatch(a,b);
  });

  const qfp=[[r16w[0],r16w[1]],[r16w[2],r16w[3]],[r16w[4],r16w[5]],[r16w[6],r16w[7]]];
  const qfw=qfp.map(([a,b],idx)=>{
    if(!ok(a,b))return a&&a!=="TBD"?a:b&&b!=="TBD"?b:"TBD";
    out.qf.push({idx,key:key(a,b)});
    return simMatch(a,b);
  });

  const sfp=[[qfw[0],qfw[1]],[qfw[2],qfw[3]]];
  const sfw=sfp.map(([a,b],idx)=>{
    if(!ok(a,b))return a&&a!=="TBD"?a:b&&b!=="TBD"?b:"TBD";
    out.sf.push({idx,key:key(a,b)});
    return simMatch(a,b);
  });

  if(ok(sfw[0],sfw[1]))out.final.push({idx:0,key:key(sfw[0],sfw[1])});
  return out;
}

// ── COMPONENTS ────────────────────────────────────────────────────────────────

function WinBar({a,b}){
  if(!a||!b)return null;
  const pa=Math.round(wp(a,b)*100),pb=100-pa;
  const ca=COLORS[a]||"#3b82f6",cb=COLORS[b]||"#475569";
  return(
    <div>
      <div style={{display:"flex",height:5,borderRadius:3,overflow:"hidden",background:"#0a1628",marginBottom:3}}>
        <div style={{width:`${pa}%`,background:ca}}/><div style={{width:`${pb}%`,background:cb}}/>
      </div>
      <div style={{display:"flex",justifyContent:"space-between",fontSize:9,color:"#475569"}}>
        <span style={{color:"#7dd3fc"}}>{fl(a)} {pa}%</span>
        <span style={{color:"#fcd34d",fontWeight:700}}>{fl(pa>pb?a:b)} {Math.max(pa,pb)}% wins if played</span>
        <span style={{color:"#7dd3fc"}}>{pb}% {fl(b)}</span>
      </div>
    </div>
  );
}

function MatchupRow({rank,a,b,count,N}){
  const prob=count/N,pct=(prob*100).toFixed(1);
  const MEDAL=["🥇","🥈","🥉"],ACC=["#4ade80","#60a5fa","#fb923c"];
  const acc=ACC[rank]||"#94a3b8";
  return(
    <div style={{
      borderLeft:`3px solid ${acc}`,borderRadius:"0 7px 7px 0",
      background:"rgba(255,255,255,.02)",padding:"8px 10px",marginBottom:6,
    }}>
      <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:5}}>
        <span style={{fontSize:16,flexShrink:0}}>{MEDAL[rank]}</span>
        <div style={{flex:1,display:"flex",flexWrap:"wrap",gap:4,alignItems:"center",minWidth:0}}>
          <span style={{fontWeight:700,fontSize:12}}>{fl(a)} {a}</span>
          <span style={{fontSize:9,color:"#475569",flexShrink:0}}>#{RANKS[a]}</span>
          <span style={{fontSize:10,color:"#475569"}}>vs</span>
          <span style={{fontWeight:700,fontSize:12}}>{fl(b)} {b}</span>
          <span style={{fontSize:9,color:"#475569",flexShrink:0}}>#{RANKS[b]}</span>
        </div>
        <div style={{textAlign:"right",flexShrink:0}}>
          <div style={{fontSize:18,fontWeight:900,color:acc,lineHeight:1}}>{pct}%</div>
          <div style={{fontSize:8,color:"#475569",whiteSpace:"nowrap"}}>chance occurs</div>
        </div>
      </div>
      <div style={{marginBottom:4}}>
        <div style={{fontSize:8,color:"#334155",marginBottom:2}}>PROBABILITY THIS MATCH HAPPENS →</div>
        <div style={{height:3,background:"#0a1628",borderRadius:2,overflow:"hidden"}}>
          <div style={{width:`${Math.min(prob*250,100)}%`,height:"100%",background:acc}}/>
        </div>
      </div>
      <WinBar a={a} b={b}/>
    </div>
  );
}

function SlotCard({slot,rows,N}){
  const tx=slot.texas;
  const parts=rows||[];
  return(
    <div style={{
      background:tx?"rgba(245,158,11,.05)":"rgba(255,255,255,.02)",
      border:`1px solid ${tx?"rgba(245,158,11,.45)":"#1a3050"}`,
      borderRadius:11,padding:"12px 14px",
    }}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:8}}>
        <div>
          <div style={{display:"flex",gap:6,alignItems:"center",marginBottom:2}}>
            <span style={{background:"#1d4ed8",color:"#fff",fontSize:10,fontWeight:800,padding:"2px 7px",borderRadius:4}}>{slot.m}</span>
            {tx&&<span style={{background:"#f59e0b",color:"#000",fontSize:9,fontWeight:800,padding:"2px 6px",borderRadius:4}}>🤠 TEXAS</span>}
          </div>
          <div style={{fontSize:10,color:"#475569"}}>{slot.desc}</div>
        </div>
        <div style={{textAlign:"right"}}>
          <div style={{fontSize:11,fontWeight:700,color:tx?"#fbbf24":"#94a3b8"}}>{slot.date}</div>
          <div style={{fontSize:9,color:"#475569",maxWidth:140,textAlign:"right"}}>{slot.venue.replace(" 🤠","")}</div>
        </div>
      </div>
      {parts.length===0
        ?<div style={{fontSize:11,color:"#334155",padding:"4px 0"}}>Simulating…</div>
        :parts.map((r,i)=><MatchupRow key={i} rank={i} a={r.a} b={r.b} count={r.count} N={N}/>)
      }
    </div>
  );
}

function GroupCard({letter,g}){
  const matches=GS[letter]||[];
  const hasTX=matches.some(m=>m.texas);
  return(
    <div style={{
      background:hasTX?"rgba(245,158,11,.04)":"rgba(255,255,255,.02)",
      border:`1px solid ${hasTX?"rgba(245,158,11,.3)":"#1a3050"}`,
      borderRadius:11,padding:"12px 14px",
    }}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
        <span style={{fontSize:10,fontWeight:800,letterSpacing:3,color:"#3b82f6"}}>GROUP {letter}</span>
        {hasTX&&<span style={{fontSize:9,color:"#f59e0b",fontWeight:700}}>🤠 TEXAS VENUE</span>}
      </div>
      <div style={{display:"flex",gap:5,flexWrap:"wrap",marginBottom:10}}>
        {g.teams.map(t=>{
          const q=g.proj.includes(t);
          return(
            <div key={t} style={{display:"flex",gap:3,alignItems:"center",padding:"3px 7px",
              background:q?"rgba(34,211,238,.1)":"rgba(255,255,255,.03)",
              border:`1px solid ${q?"rgba(34,211,238,.3)":"#1a3050"}`,borderRadius:5,fontSize:11}}>
              <span>{fl(t)}</span><span style={{fontWeight:q?700:400}}>{t}</span>
              <span style={{fontSize:8,color:"#475569"}}>#{RANKS[t]}</span>
              {q&&<span style={{fontSize:8,color:"#22d3ee"}}>✓</span>}
            </div>
          );
        })}
      </div>
      {matches.map((m,i)=>(
        <div key={i} style={{
          display:"flex",alignItems:"center",gap:6,padding:"4px 7px",marginBottom:3,
          background:m.texas?"rgba(245,158,11,.07)":"rgba(255,255,255,.02)",
          border:`1px solid ${m.texas?"rgba(245,158,11,.3)":"#152035"}`,borderRadius:5,
        }}>
          <span style={{fontSize:9,color:"#475569",whiteSpace:"nowrap",minWidth:38}}>{m.date}</span>
          <span style={{fontSize:11,fontWeight:600}}>{fl(m.a)} {m.a}</span>
          <span style={{fontSize:9,color:"#475569"}}>vs</span>
          <span style={{fontSize:11,fontWeight:600}}>{fl(m.b)} {m.b}</span>
          <span style={{flex:1,textAlign:"right",fontSize:9,color:m.texas?"#fbbf24":"#475569",
            overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
            {m.venue.replace(" 🤠","")}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── MAIN APP ──────────────────────────────────────────────────────────────────
const TABS=[
  {id:"rankings",label:"📊 FIFA Rankings"},
  {id:"groups",  label:"🏟️ Group Stage"},
  {id:"r32",     label:"Round of 32",n:16},
  {id:"r16",     label:"Round of 16", n:8},
  {id:"qf",      label:"Quarterfinals",n:4},
  {id:"sf",      label:"Semifinals",  n:2},
  {id:"final",   label:"⭐ Final",    n:1},
];
const N=10000;

export default function App(){
  const[tab,setTab]=useState("rankings");
  const[simData,setSimData]=useState(null);
  const[progress,setProgress]=useState(0);

  useEffect(()=>{
    const sc={
      r32:Array.from({length:16},()=>({})),
      r16:Array.from({length:8}, ()=>({})),
      qf: Array.from({length:4}, ()=>({})),
      sf: Array.from({length:2}, ()=>({})),
      final:[{}],
    };
    let done=0;
    const chunk=()=>{
      const end=Math.min(done+500,N);
      for(;done<end;done++){
        const sim=runOnce();
        for(const[round,entries]of Object.entries(sim)){
          for(const{idx,key}of entries){
            sc[round][idx][key]=(sc[round][idx][key]||0)+1;
          }
        }
      }
      setProgress(Math.round(done/N*100));
      if(done<N){setTimeout(chunk,0);return;}
      const res={};
      for(const[round,slots]of Object.entries(sc)){
        res[round]=slots.map(slotObj=>
          Object.entries(slotObj)
            .sort(([,a],[,b])=>b-a).slice(0,3)
            .map(([k,count])=>{const[a,b]=k.split("|");return{a,b,count};})
        );
      }
      setSimData(res);
    };
    setTimeout(chunk,100);
  },[]);

  const qualTeams=SORTED_ELO.filter(([t])=>Object.values(GROUPS).some(g=>g.teams.includes(t)));

  return(
    <div style={{fontFamily:"'DM Sans','Trebuchet MS',sans-serif",background:"#040d1c",minHeight:"100vh",color:"#e2e8f0"}}>

      {/* HEADER */}
      <div style={{background:"linear-gradient(135deg,#071428,#0d2040,#071428)",borderBottom:"1px solid #152035",padding:"16px 14px 12px",position:"relative",overflow:"hidden"}}>
        <div style={{position:"absolute",inset:0,backgroundImage:"radial-gradient(ellipse at 10% 50%,rgba(37,99,235,.1),transparent 50%),radial-gradient(ellipse at 90% 50%,rgba(245,158,11,.09),transparent 50%)",pointerEvents:"none"}}/>
        <div style={{position:"relative"}}>
          <div style={{fontSize:9,letterSpacing:4,color:"#3b82f6",fontWeight:700,marginBottom:3}}>FIFA WORLD CUP 2026 · FULL BRACKET PREDICTOR</div>
          <h1 style={{margin:"0 0 3px",fontSize:19,fontWeight:900,background:"linear-gradient(90deg,#fff 20%,#60a5fa 65%,#fbbf24 100%)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
            All Knockout Matches · Top 3 Matchup Probabilities
          </h1>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{fontSize:10,color:"#475569"}}>
              {simData?"✓ ":"⚙️ "}{N.toLocaleString()} simulations · Official FIFA Apr 2026 rankings · Exact bracket
              {!simData&&` · ${progress}%`}
            </div>
            {!simData&&(
              <div style={{width:100,height:4,background:"#0f1f3d",borderRadius:2,overflow:"hidden"}}>
                <div style={{width:`${progress}%`,height:"100%",background:"linear-gradient(90deg,#1d4ed8,#60a5fa)",transition:"width .3s"}}/>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* TABS */}
      <div style={{display:"flex",gap:2,padding:"8px 12px 0",borderBottom:"1px solid #152035",overflowX:"auto",background:"#040d1c",scrollbarWidth:"none"}}>
        {TABS.map(tb=>(
          <button key={tb.id} onClick={()=>setTab(tb.id)} style={{
            background:tab===tb.id?"#1d4ed8":"transparent",
            color:tab===tb.id?"#fff":"#475569",
            border:`1px solid ${tab===tb.id?"#3b82f6":"#1a3050"}`,
            borderRadius:"6px 6px 0 0",padding:"6px 10px",fontSize:11,
            fontWeight:tab===tb.id?700:500,cursor:"pointer",whiteSpace:"nowrap",flexShrink:0,
          }}>
            {tb.label}
            {tb.n&&<span style={{marginLeft:4,background:"rgba(255,255,255,.15)",borderRadius:8,padding:"1px 5px",fontSize:9}}>{tb.n}</span>}
          </button>
        ))}
      </div>

      <div style={{padding:"14px 12px 40px"}}>

        {/* RANKINGS */}
        {tab==="rankings"&&(
          <div>
            <div style={{fontSize:11,color:"#475569",marginBottom:10}}>
              Official FIFA/Coca-Cola Men's World Ranking · 01 April 2026 · Used directly as Elo scores for all probability calculations below
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))",gap:6}}>
              {qualTeams.map(([name,pts])=>{
                const f=FORM[name]||0;
                return(
                  <div key={name} style={{display:"flex",alignItems:"center",gap:8,background:"rgba(255,255,255,.025)",border:"1px solid #152035",borderRadius:7,padding:"7px 10px"}}>
                    <div style={{textAlign:"center",minWidth:26}}>
                      <div style={{fontSize:16}}>{fl(name)}</div>
                      <div style={{fontSize:8,color:"#475569",fontWeight:700}}>#{RANKS[name]}</div>
                    </div>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:3}}>
                        <span style={{fontWeight:700,fontSize:12,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{name}</span>
                        <div style={{display:"flex",gap:5,alignItems:"center",flexShrink:0}}>
                          <span style={{fontSize:9,color:"#94a3b8",fontFamily:"monospace"}}>{pts}pts</span>
                          <span style={{fontSize:9,padding:"1px 4px",borderRadius:4,fontWeight:700,
                            background:fc(f)+"18",color:fc(f),border:`1px solid ${fc(f)}44`}}>
                            {f>0?"+":""}{f.toFixed(1)} {fa(f)}
                          </span>
                        </div>
                      </div>
                      <div style={{height:4,background:"#0a1628",borderRadius:2,overflow:"hidden"}}>
                        <div style={{width:`${((pts-950)/(1877-950))*100}%`,height:"100%",background:COLORS[name]||"#1d4ed8"}}/>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* GROUP STAGE */}
        {tab==="groups"&&(
          <div>
            <div style={{fontSize:11,color:"#475569",marginBottom:10}}>
              All 72 group stage matches · Jun 11–27 · ✓ = projected qualifier (Elo-based) · 🤠 = Texas venue
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))",gap:10}}>
              {Object.entries(GROUPS).map(([ltr,g])=>(
                <GroupCard key={ltr} letter={ltr} g={g}/>
              ))}
            </div>
          </div>
        )}

        {/* KNOCKOUT ROUND TABS */}
        {["r32","r16","qf","sf","final"].map(round=>(
          tab===round&&(
            <div key={round}>
              <div style={{fontSize:11,color:"#475569",marginBottom:10}}>
                <b style={{color:"#60a5fa"}}>How to read:</b> Each match slot shows the 3 most likely team combinations across {N.toLocaleString()} simulations.
                The <b>%</b> is how often that exact matchup occurs. The bar below shows who wins <i>if</i> it happens.
                {round==="r32"&&" · 16 matches · Jun 28–Jul 3"}
                {round==="r16"&&" · 8 matches · Jul 4–7"}
                {round==="qf"&&" · 4 matches · Jul 9–11"}
                {round==="sf"&&" · 2 matches · Jul 14–15 · M101 at Dallas AT&T 🤠"}
                {round==="final"&&" · Jul 19 · East Rutherford, NJ"}
              </div>
              <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(360px,1fr))",gap:10}}>
                {KO[round].map((slot,i)=>(
                  <SlotCard key={slot.m} slot={slot} rows={simData?simData[round][i]:null} N={N}/>
                ))}
              </div>
            </div>
          )
        ))}

      </div>
    </div>
  );
}
