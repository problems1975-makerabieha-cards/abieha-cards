<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UNO أبيها - النهائي</title>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<style>
*{box-sizing:border-box}
:root{--gold:#ffd166;--dark:#050b18;--panel:rgba(6,18,42,.78)}
body{margin:0;min-height:100vh;font-family:Arial,Tahoma,sans-serif;color:white;text-align:center;background:radial-gradient(circle at 50% 0%,rgba(70,140,255,.28),transparent 35%),linear-gradient(180deg,#0c234a,#050b18 75%)}
main{max-width:1320px;margin:auto;padding:clamp(8px,2vw,16px)}
h1{margin:8px 0 10px;text-shadow:0 4px 10px #000;font-size:clamp(22px,5vw,36px)}
.join,.controls,.logBox{background:linear-gradient(135deg,rgba(22,53,105,.95),rgba(7,17,38,.95));border:1px solid rgba(120,190,255,.25);border-radius:24px;padding:12px;margin-bottom:14px;box-shadow:0 18px 55px #0008}
input,select{border:0;border-radius:14px;padding:12px 14px;margin:6px;font-size:16px;min-width:160px}
button{border:0;border-radius:15px;padding:12px 18px;margin:6px;font-weight:900;cursor:pointer;color:#071126;background:linear-gradient(180deg,#fff0a6,#ffd166);box-shadow:0 7px 0 #9b6a00,0 12px 22px #0008}
button:active{transform:translateY(4px);box-shadow:0 3px 0 #9b6a00}
.green{background:linear-gradient(180deg,#7affb2,#35dd7b);box-shadow:0 7px 0 #0b7d3b,0 12px 22px #0008}
.blueBtn{background:linear-gradient(180deg,#79c6ff,#2f80ff);color:white;box-shadow:0 7px 0 #06449d,0 12px 22px #0008}
.redBtn{background:linear-gradient(180deg,#ff8aa0,#ff4d6d);color:white;box-shadow:0 7px 0 #a50d28,0 12px 22px #0008}
.hidden{display:none!important}
.avatarSelectWrap{display:inline-flex;align-items:center;gap:6px;background:rgba(0,0,0,.18);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:4px 8px;margin:6px}
#avatarInput{min-width:86px;font-size:22px;padding:8px 10px;margin:0}

/* ===== ARENA ===== */
.arena{position:relative;min-height:780px;border-radius:clamp(20px,4vw,34px);overflow:visible;padding:clamp(10px,2vw,22px);padding-bottom:260px;background:radial-gradient(circle at 50% 42%,rgba(68,140,255,.20),transparent 43%),linear-gradient(135deg,rgba(20,55,105,.8),rgba(5,10,24,.97));border:1px solid rgba(120,190,255,.26);box-shadow:inset 0 0 120px #0009,0 26px 85px #000b}
.table{position:absolute;left:50%;top:39%;transform:translate(-50%,-50%);width:min(90vw,1040px);height:clamp(430px,58vh,570px);border-radius:50%;background:linear-gradient(rgba(0,0,0,.15),rgba(0,0,0,.28)),url('/static/bg-table.png') center/contain no-repeat,#050505;border:clamp(5px,1.3vw,10px) solid rgba(255,255,255,.12);box-shadow:inset 0 0 70px rgba(0,0,0,.55),0 0 0 6px rgba(76,201,240,.15),0 35px 85px #000c}
.tableInfo{position:relative;z-index:2;height:100%;display:grid;place-items:center}.info{position:relative;min-width:0;padding:0;background:transparent;border:0;box-shadow:none}
#timeText{font-size:13px;opacity:.92;margin-bottom:12px;position:relative;z-index:40}#penaltyLine{font-size:14px;min-height:18px;margin:0 0 6px;color:#fff;text-shadow:0 3px 8px #000;position:relative;z-index:40}

/* ===== CENTER PLAY ===== */
.centerPlayArea{position:relative;display:flex;align-items:center;justify-content:center;gap:0;width:280px;height:260px;margin:auto}
#top{display:flex;justify-content:center;align-items:center;position:relative;z-index:25}
#top .card{width:125px;height:185px;font-size:54px;transform:rotate(-7deg);z-index:25}#top .card .mark{font-size:58px}
.drawOutsideBtn{position:absolute;right:-118px;top:50%;transform:translateY(-50%) rotate(-7deg);width:108px;height:72px;font-size:20px;z-index:80;display:flex;align-items:center;justify-content:center;border:3px solid #fff3b0;box-shadow:0 0 22px rgba(255,209,102,.9),0 8px 0 #9b6a00,0 14px 24px #0008}
.ovalInfo{position:absolute;left:-150px;top:50%;transform:translateY(-50%);width:176px;min-height:78px;border-radius:18px;background:rgba(0,0,0,.45);border:2px solid rgba(255,255,255,.7);display:flex;flex-direction:column;justify-content:center;text-align:center;font-weight:900;z-index:80}

/* ===== CARDS ===== */
.card{display:inline-flex;align-items:center;justify-content:center;position:relative;width:76px;height:112px;border-radius:19px;margin:4px;font-size:28px;font-weight:900;cursor:pointer;border:4px solid #fff8e8;box-shadow:0 10px 18px #0009;overflow:hidden;transition:.14s;isolation:isolate}.card:hover{filter:brightness(1.08)}
.red{background:linear-gradient(145deg,#ff4b66,#aa071b)}.bluec{background:linear-gradient(145deg,#45b6ff,#064dbb)}.greenc{background:linear-gradient(145deg,#46ee91,#04783a)}.yellow{background:linear-gradient(145deg,#ffe56a,#d69000);color:#1b1600}.black{background:linear-gradient(145deg,#333,#050505)}
.card::before{content:"";position:absolute;right:7%;top:6%;width:30%;aspect-ratio:1;border-radius:50%;background:rgba(255,255,255,.22);box-shadow:0 2px 8px #0009;border:1px solid rgba(255,255,255,.55);z-index:1}.card::after{content:"أبيها";position:absolute;left:8%;bottom:6%;font-size:13px;letter-spacing:.3px;opacity:.95;padding:2px 7px;border-radius:999px;background:rgba(0,0,0,.33);border:1px solid rgba(255,255,255,.22);z-index:2}
.card .mark{position:absolute;top:53%;left:50%;transform:translate(-50%,-50%);font-size:34px;text-shadow:0 3px 8px #000;z-index:3;font-family:Arial,Tahoma,sans-serif;font-weight:900}.card .skullBig{position:absolute;top:20%;left:50%;transform:translateX(-50%);font-size:58px;opacity:.18;z-index:0;filter:drop-shadow(0 4px 8px #000)}
.cornerNum{position:absolute;right:7%;top:6%;width:30%;aspect-ratio:1;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;color:#fff;text-shadow:0 2px 5px #000;z-index:8;pointer-events:none;line-height:1}.hand .cornerNum{font-size:16px}#top .cornerNum{font-size:22px}

/* ===== SEATS ===== */
.seat{position:absolute;width:118px;min-height:70px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;padding:7px;border-radius:18px;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.18);box-shadow:none;overflow:hidden;z-index:10}.seat.active{outline:4px solid var(--gold);box-shadow:0 0 35px rgba(255,209,102,.9)}
.s1{right:5%;top:48%;bottom:auto}.s2{right:8%;top:12%}.s3{left:50%;top:4%;transform:translateX(-50%)}.s4{left:8%;top:12%}.s5{left:5%;top:48%;bottom:auto}
.playerName{font-weight:900;font-size:clamp(12px,2.2vw,17px);max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 2px 5px #000}.playerMeta{font-size:clamp(10px,1.8vw,13px);opacity:.9;line-height:1.35}.playerCards{font-weight:900;color:var(--gold)}.playerScore{margin-top:3px;color:#ffd166;font-weight:900;font-size:clamp(10px,1.8vw,13px);text-shadow:0 0 8px #000,0 0 10px rgba(255,209,102,.35)}.playerScore.danger{color:#ff4d6d;animation:scorePulse .9s infinite ease-in-out}@keyframes scorePulse{0%,100%{transform:scale(1);filter:brightness(1)}50%{transform:scale(1.08);filter:brightness(1.25)}}.seat.empty{opacity:.22}
.avatarBadge{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;font-size:26px;background:radial-gradient(circle at 35% 25%,rgba(255,255,255,.35),rgba(255,209,102,.20) 45%,rgba(0,0,0,.45));border:2px solid rgba(255,255,255,.75);box-shadow:0 0 14px rgba(255,209,102,.45),0 8px 18px #0009;margin-bottom:3px;line-height:1}.seat.active .avatarBadge{animation:avatarBounce 1.05s infinite ease-in-out}@keyframes avatarBounce{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-5px) scale(1.08)}}

/* ===== MY HAND ===== */
.seat.s0.me{left:50%;bottom:-30px;transform:translateX(-50%);width:100%;max-width:100vw;min-height:255px;background:transparent;border:0;box-shadow:none;z-index:60;overflow:hidden;padding-inline:12px}.seat.s0.me .avatarBadge{width:34px;height:34px;font-size:22px;display:inline-grid;margin:0 0 2px}.seat.s0.me .playerName,.seat.s0.me .playerMeta{position:relative;top:0;margin-bottom:4px;z-index:90}
.seat.s0.me .hand{width:100%;max-width:100%;min-height:205px;display:flex;align-items:flex-end;justify-content:flex-start;overflow-x:auto;overflow-y:visible;background:transparent;border:0;padding:30px 18px 35px;gap:0;transform:none;scrollbar-width:thin;white-space:nowrap}.seat.s0.me .hand .card{flex:0 0 auto;width:78px;height:116px;margin-left:-12px;transform-origin:bottom center;transition:transform .18s ease,filter .18s ease}.seat.s0.me .hand .card:first-child{margin-left:0}.seat.s0.me .hand .card:nth-child(odd){transform:rotate(-7deg) translateY(6px)}.seat.s0.me .hand .card:nth-child(even){transform:rotate(7deg) translateY(6px)}.seat.s0.me .hand .card:hover{transform:translateY(-22px) scale(1.08)!important;z-index:99;filter:brightness(1.12)}

/* ===== CHAT ===== */
.log{height:128px;overflow:auto;background:rgba(0,0,0,.38);border-radius:16px;padding:10px;line-height:1.7;text-align:right}#timerBar{height:10px;background:linear-gradient(to right,red,orange);width:100%}#colorPicker{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;place-items:center;z-index:999}#colorPicker.show{display:grid}.pickerBox{background:#111;padding:20px;border-radius:20px}.pickerBox button{width:60px;height:60px;margin:10px;border-radius:50%;border:none;cursor:pointer}.timerSetup{display:inline-flex;align-items:center;gap:6px;background:rgba(0,0,0,.24);padding:8px 10px;border-radius:16px;margin:6px}.timerSetup select{min-width:100px;margin:0}


/* ===== FINAL RESULTS ===== */
.finalOverlay{position:fixed;inset:0;background:rgba(0,0,0,.78);display:none;place-items:center;z-index:2000;padding:16px}
.finalOverlay.show{display:grid}
.finalBox{width:min(92vw,620px);background:linear-gradient(135deg,rgba(22,53,105,.98),rgba(5,10,24,.98));border:2px solid var(--gold);border-radius:28px;padding:22px;box-shadow:0 0 50px rgba(255,209,102,.35),0 30px 90px #000;color:#fff;text-align:center}
.finalBox h2{margin:0 0 12px;font-size:clamp(24px,5vw,36px);color:var(--gold);text-shadow:0 3px 10px #000}
.finalWinner{font-size:clamp(20px,4vw,30px);font-weight:900;margin:10px 0 16px;color:#7affb2;text-shadow:0 0 12px rgba(122,255,178,.5)}
.finalTable{width:100%;border-collapse:collapse;margin-top:12px;overflow:hidden;border-radius:14px}
.finalTable th,.finalTable td{padding:10px;border-bottom:1px solid rgba(255,255,255,.14);font-weight:900}
.finalTable th{color:#071126;background:linear-gradient(180deg,#fff0a6,#ffd166)}
.finalLoser{color:#ff6b83}

/* ===== RESPONSIVE ===== */
@media(max-width:900px){.arena{min-height:730px;padding-bottom:245px}.table{width:92vw;height:440px}.seat.s0.me .hand .card{width:70px;height:104px;margin-left:-10px}.drawOutsideBtn{right:-92px;width:88px;height:60px;font-size:17px}.ovalInfo{left:-118px;width:138px;font-size:13px}}
@media(max-width:760px){input,select{min-width:128px;font-size:14px;padding:10px}button{padding:10px 12px;margin:4px;border-radius:13px}.join,.controls,.logBox{border-radius:18px;padding:8px}.arena{min-height:690px;padding-bottom:225px}.table{top:38%;width:96vw;height:370px}.centerPlayArea{width:220px;height:210px}#top .card{width:95px;height:142px}.drawOutsideBtn{right:-66px;width:66px;height:48px;font-size:14px}.ovalInfo{left:-82px;width:110px;min-height:60px;font-size:11px}.seat:not(.me){width:88px;min-height:58px;font-size:11px}.s1{right:2%;top:50%}.s2{right:4%;top:13%}.s3{top:1%}.s4{left:4%;top:13%}.s5{left:2%;top:50%}.seat.s0.me{bottom:-15px;min-height:230px}.seat.s0.me .hand{padding-inline:12px}.seat.s0.me .hand .card{width:62px;height:94px;margin-left:-8px}.avatarBadge{width:34px;height:34px;font-size:21px}.seat.s0.me .avatarBadge{width:30px;height:30px;font-size:20px}.log{height:90px;font-size:12px}}
@media(max-width:480px){.arena{min-height:650px;padding-bottom:205px}.table{width:96vw;height:350px}.centerPlayArea{width:190px;height:190px}#top .card{width:86px;height:128px}.seat:not(.me){width:76px;min-height:52px}.seat.s0.me .hand .card{width:58px;height:88px;margin-left:-8px}#avatarInput{min-width:76px;font-size:20px}}
</style>
</head>
<body>
<main>
<h1>UNO أبيها - النهائي</h1>

<div class="join" id="joinBox">
  <input id="nameInput" placeholder="اسم اللاعب">
  <span class="avatarSelectWrap">🎭 <select id="avatarInput" title="اختر شخصيتك الكوميدية">
    <option value="auto">تلقائي</option><option value="🤡">🤡</option><option value="😂">😂</option><option value="😈">😈</option><option value="🤖">🤖</option><option value="👽">👽</option><option value="🐸">🐸</option><option value="🐵">🐵</option><option value="🐔">🐔</option><option value="💀">💀</option><option value="🧠">🧠</option><option value="🥸">🥸</option><option value="👻">👻</option>
  </select></span>
  <input id="roomInput" value="ROOM1">
  <select id="modeInput" onchange="toggleTeamOptions()"><option value="solo">فردي</option><option value="teams">جماعي</option></select>
  <select id="teamModeInput" class="teamOnly hidden" onchange="toggleTeamOptions()"><option value="auto">تلقائي</option><option value="manual">يدوي</option></select>
  <select id="teamCountInput" class="teamOnly hidden"><option value="2">فريقين</option><option value="3">3 فرق</option></select>
  <select id="teamInput" class="manualOnly hidden"><option value="A">أزرق</option><option value="B">برتقالي</option><option value="C">بنفسجي</option></select>
  <button class="green" onclick="joinGame()">دخول</button>
</div>

<div class="controls hidden" id="controls">
  <span class="timerSetup">⏱️ وقت اللاعب قبل البداية: <select id="timeLimitInput"><option value="10">10 ثواني</option><option value="15">15 ثانية</option><option value="20">20 ثانية</option><option value="30" selected>30 ثانية</option><option value="45">45 ثانية</option><option value="60">60 ثانية</option><option value="90">90 ثانية</option><option value="120">120 ثانية</option></select></span>
  <span class="timerSetup">🎯 سكور اللعبة: <select id="scoreLimitInput"><option value="200">200</option><option value="300">300</option><option value="400">400</option><option value="500" selected>500</option></select></span>
  <button class="blueBtn" onclick="startGame()">ابدأ</button><button onclick="lastCard()">كرت أخير</button><button class="redBtn" onclick="endGame()">إنهاء اللعبة</button><button onclick="leaveGame()">رجوع / خروج من الغرفة</button>
</div>

<section class="arena hidden" id="arena">
  <div id="timerBar"></div>
  <div class="table"><div class="tableInfo"><div class="info"><h3 id="penaltyLine"></h3><div id="timeText"></div><div class="centerPlayArea"><div id="top"></div><button class="drawOutsideBtn" onclick="drawCard()">اسحب</button><div class="ovalInfo"><div id="turn">-</div><div id="need">-</div></div></div></div></div></div>
  <div class="seat s0 me" id="seat0"><div id="hand" class="hand"></div></div>
  <div class="seat s1" id="seat1"></div><div class="seat s2" id="seat2"></div><div class="seat s3" id="seat3"></div><div class="seat s4" id="seat4"></div><div class="seat s5" id="seat5"></div>
</section>

<section class="logBox hidden" id="logBox"><div id="log" class="log"></div><div style="display:flex;gap:6px;margin-top:8px"><input id="chatInput" placeholder="اكتب رسالة..." style="flex:1;min-width:0"><button onclick="sendChat()">إرسال</button></div></section>

<div id="colorPicker"><div class="pickerBox"><button style="background:red" onclick="chooseColor('red')"></button><button style="background:blue" onclick="chooseColor('bluec')"></button><button style="background:green" onclick="chooseColor('greenc')"></button><button style="background:gold" onclick="chooseColor('yellow')"></button></div></div>

<div id="finalOverlay" class="finalOverlay"><div class="finalBox"><h2>🏆 النتيجة النهائية</h2><div id="finalWinner" class="finalWinner"></div><div id="finalLosers"></div><table class="finalTable"><thead><tr><th>اللاعب</th><th>النقاط</th><th>الجولات</th></tr></thead><tbody id="finalRows"></tbody></table><button class="blueBtn" onclick="closeFinalOverlay()">إغلاق</button></div></div>

<script>
const socket = io();
let roomCode = "";
let myId = null;
let state = null;
let selectedIndex = null;
let selectedAvatar = "auto";
const COMEDY_AVATARS = ["🤡","😂","😈","🤖","👽","🐸","🐵","🐔","💀","🧠","🥸","👻","🦖","🦄"];
function simpleHash(str){let h=0;str=String(str||"");for(let i=0;i<str.length;i++)h=((h<<5)-h+str.charCodeAt(i))|0;return Math.abs(h)}
function avatarForPlayer(p){if(!p)return"🤡";if(p.avatar&&p.avatar!=="auto")return p.avatar;if(p.id===myId&&selectedAvatar&&selectedAvatar!=="auto")return selectedAvatar;return COMEDY_AVATARS[simpleHash((p.id||"")+(p.name||""))%COMEDY_AVATARS.length]}
function avatarHtml(p){return `<div class="avatarBadge" title="شخصية اللاعب">${avatarForPlayer(p)}</div>`}
function sendChat(){const input=document.getElementById("chatInput");const text=input.value.trim();if(!text)return;socket.emit("chat",{room:roomCode,playerId:myId,text});input.value=""}
function toggleTeamOptions(){const mode=document.getElementById("modeInput").value;const teamMode=document.getElementById("teamModeInput").value;document.querySelectorAll(".teamOnly").forEach(x=>x.classList.toggle("hidden",mode!=="teams"));document.querySelectorAll(".manualOnly").forEach(x=>x.classList.toggle("hidden",!(mode==="teams"&&teamMode==="manual")))}
function kickPlayer(targetId){if(!confirm("تأكيد طرد اللاعب؟"))return;socket.emit("kick_player",{room:roomCode,hostId:myId,targetId})}
socket.on("kicked",()=>{alert("تم طردك من الغرفة");location.reload()});
function joinGame(){const name=document.getElementById("nameInput").value||"لاعب";selectedAvatar=document.getElementById("avatarInput")?.value||"auto";roomCode=(document.getElementById("roomInput").value||"ROOM1").toUpperCase();const mode=document.getElementById("modeInput").value;const teamMode=document.getElementById("teamModeInput").value;const teamCount=document.getElementById("teamCountInput").value;const team=document.getElementById("teamInput").value;socket.emit("join",{name,room:roomCode,mode,teamMode,teamCount,team,avatar:selectedAvatar})}
socket.on("joined",data=>{myId=data.playerId;roomCode=data.room;document.getElementById("joinBox").classList.add("hidden");document.getElementById("controls").classList.remove("hidden");document.getElementById("arena").classList.remove("hidden");document.getElementById("logBox").classList.remove("hidden")});
socket.on("error_msg",msg=>alert(msg));
function startGame(){const timeLimit=parseInt(document.getElementById("timeLimitInput")?.value||"30",10);const scoreLimit=parseInt(document.getElementById("scoreLimitInput")?.value||"500",10);socket.emit("start",{room:roomCode,playerId:myId,timeLimit,scoreLimit})}
function drawCard(){socket.emit("draw",{room:roomCode,playerId:myId})}function lastCard(){socket.emit("last_card",{room:roomCode,playerId:myId})}function endGame(){socket.emit("end_game",{room:roomCode,playerId:myId})}function leaveGame(){socket.emit("leave_room",{room:roomCode,playerId:myId})}socket.on("left_room",()=>{location.reload()});
function playCard(i){const card=state.myHand[i];if(card.c==="black"){selectedIndex=i;document.getElementById("colorPicker").classList.add("show")}else{socket.emit("play",{room:roomCode,playerId:myId,index:i})}}
function chooseColor(color){socket.emit("play",{room:roomCode,playerId:myId,index:selectedIndex,color});document.getElementById("colorPicker").classList.remove("show")}
socket.on("state",data=>{state=data;render()});
function cardSymbol(n){if(n==="عكس")return"↺";if(n==="تخطي")return"⊘";return n}
function cardValueOrder(n){const v=parseInt(n,10);if(!Number.isNaN(v))return v;if(n==="تخطي")return 10;if(n==="عكس")return 11;if(n==="+2")return 12;if(n==="+4")return 13;if(n==="لون")return 14;return 99}
function colorOrder(c){return({bluec:1,yellow:2,red:3,greenc:4,black:5})[c]||99}
function sortedHandWithIndex(hand){return(hand||[]).map((c,i)=>({...c,realIndex:i})).sort((a,b)=>{const ca=colorOrder(a.c),cb=colorOrder(b.c);if(ca!==cb)return ca-cb;return cardValueOrder(a.n)-cardValueOrder(b.n)})}
function cardHtml(c){
  const symbol = cardSymbol(c.n);
  return `<div class="card ${c.c}" onclick="playCard(${c.realIndex})">
    <span class="cornerNum">${symbol}</span>
    <span class="skullBig">☠</span>
    <span class="mark">${symbol}</span>
  </div>`;
}
function tableCardHtml(c){const symbol=cardSymbol(c.n);return `<div class="card ${c.c}"><span class="cornerNum">${symbol}</span><span class="skullBig">☠</span><span class="mark">${symbol}</span></div>`}
function scoreHtml(p){const score=Number(p?.score||0);const limit=Number(state?.scoreLimit||500);const cls=score>=Math.max(0,limit-50)?"playerScore danger":"playerScore";return `<div class="${cls}">النقاط: ${score} / ${limit}</div>`}

function closeFinalOverlay(){document.getElementById("finalOverlay")?.classList.remove("show")}
function renderFinalResults(){
  const overlay=document.getElementById("finalOverlay");
  if(!overlay||!state)return;
  const fr=state.finalResults;
  if(!state.gameOver||!fr){overlay.classList.remove("show");return;}
  document.getElementById("finalWinner").innerHTML="الفائز: "+(fr.winner||"-");
  const losers=Array.isArray(fr.losers)?fr.losers:[];
  document.getElementById("finalLosers").innerHTML=losers.length?`<div class="finalLoser">الخاسر: ${losers.join("، ")}</div>`:"";
  const rows=(fr.players||[]).map(p=>`<tr><td>${p.name||"-"}</td><td>${p.score||0}</td><td>${p.wins||0}</td></tr>`).join("");
  document.getElementById("finalRows").innerHTML=rows;
  overlay.classList.add("show");
}
function render(){if(!state)return;document.getElementById("turn").innerHTML="🔥 الدور: "+state.players[state.turn].name;const colorMap={red:"#ff4b4b",yellow:"#ffd84d",greenc:"#35d66b",bluec:"#4da3ff",black:"#ffffff"};document.getElementById("need").innerHTML="اللون: <span style='color:"+(colorMap[state.color]||"#fff")+"'>"+state.color+"</span>";let penalty="";if(state.pendingDraw4>0)penalty="عقوبة +4: "+state.pendingDraw4+" — رد بنفس اللون أو اسحب";else if(state.pendingDraw2>0)penalty="عكس/تخطي: رد بنفس اللون أو اسحب كرتين";document.getElementById("penaltyLine").innerHTML=penalty;document.getElementById("top").innerHTML=state.top?tableCardHtml(state.top):"";document.getElementById("hand").innerHTML=sortedHandWithIndex(state.myHand).map(c=>cardHtml(c)).join("");document.getElementById("log").innerHTML=(state.log||[]).join("<br>");const percent=state.timeLimit?Math.max(0,Math.min(100,(state.timeLeft/state.timeLimit)*100)):0;document.getElementById("timerBar").style.width=percent+"%";document.getElementById("timeText").innerHTML=state.started?("⏱️ الوقت المتبقي: "+state.timeLeft+" ثانية"):("⏱️ وقت اللاعب: "+state.timeLimit+" ثانية");renderSeats();renderFinalResults()}
function renderSeats(){if(!state||!state.players)return;const players=state.players;const meIndex=players.findIndex(p=>p.id===myId);for(let i=0;i<6;i++){const seat=document.getElementById("seat"+i);if(!seat)continue;seat.classList.toggle("active",false);if(i===0){const me=players[meIndex]||players[0];seat.classList.toggle("empty",!me);if(me){const hand=document.getElementById("hand");seat.querySelectorAll(".avatarBadge,.playerName,.playerMeta,.playerScore").forEach(x=>x.remove());seat.insertAdjacentHTML("afterbegin",`${avatarHtml(me)}<div class="playerName">${me.name}</div><div class="playerMeta"><span class="playerCards">${(state.myHand||[]).length}</span> كرت${scoreHtml(me)}</div>`);if(players[state.turn]&&players[state.turn].id===me.id)seat.classList.add("active");if(hand&&hand.parentElement!==seat)seat.appendChild(hand)}continue}const idx=meIndex>=0?(meIndex+i)%players.length:i;const p=players[idx];if(!p||idx===meIndex||i>=players.length){seat.classList.add("empty");seat.innerHTML="";continue}seat.classList.remove("empty");const teamTxt=p.team?` — ${p.team}`:"";const kickBtn=state.host===myId&&p.id!==myId?`<button class="redBtn" onclick="kickPlayer('${p.id}')">طرد</button>`:"";seat.innerHTML=`${avatarHtml(p)}<div class="playerName">${p.name}</div><div class="playerMeta"><span class="playerCards">${p.count??p.cards??0}</span> كرت${teamTxt}${scoreHtml(p)}</div>${kickBtn}`;if(players[state.turn]&&players[state.turn].id===p.id)seat.classList.add("active")}}
</script>
</main>
</body>
</html>        socketio.emit("state", payload, room=p["sid"])

def find_player(room, player_id):
    if room not in rooms:
        return -1
    for i, p in enumerate(rooms[room]["players"]):
        if p["id"] == player_id:
            return i
    return -1

def assign_auto_team(r):
    count = max(2, min(3, int(r.get("teamCount", 2) or 2)))
    valid = TEAM_ORDER[:count]
    return valid[len(r["players"]) % len(valid)]

def is_allowed(r, card):
    top = r["discard"][-1]

    # إذا فيه عقوبة +4: لا أرقام، فقط +4 أو عكس/تخطي بنفس اللون
    if r.get("pendingDraw4", 0) > 0:
        return card["n"] == "+4" or (
            card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"]
        )

    # إذا فيه عقوبة +2: لا أرقام، فقط +2/+4 أو عكس/تخطي حسب الكرت أو اللون
    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] in ["+2", "+4"] or
            (
                card["n"] in ["عكس", "تخطي"] and
                (card["n"] == top["n"] or card["c"] == r["color"])
            )
        )

    # الوضع العادي: بعد تخطي/عكس تقدر تلعب رقم إذا نفس اللون
    return card["c"] == "black" or card["c"] == r["color"] or card["n"] == top["n"]
    # During Skip/Reverse challenge: player may answer with Skip/Reverse in the requested color,
    # otherwise the Draw button makes them draw two cards.
def is_allowed(r, card):
    top = r["discard"][-1]

    # إذا فيه عقوبة +4: لا أرقام
    if r.get("pendingDraw4", 0) > 0:
        return card["n"] == "+4" or (
            card["n"] in ["عكس", "تخطي"] and card["c"] == r["color"]
        )

    # إذا فيه عقوبة +2: لا أرقام
    if r.get("pendingDraw2", 0) > 0:
        return (
            card["n"] in ["+2", "+4"] or
            (
                card["n"] in ["عكس", "تخطي"] and
                (
                    card["n"] == top["n"] or
                    card["c"] == r["color"]
                )
            )
        )

    # اللعب العادي:
    # إذا الموجود عكس/تخطي، يسمح برقم نفس اللون
    return card["c"] == "black" or card["c"] == r["color"] or card["n"] == top["n"]

def apply_effect(r, card):
    # +2 (stack)
    if card["n"] == "+2":
        r["pendingDraw2"] = int(r.get("pendingDraw2", 0)) + 2
        r["log"].insert(0, f"العقوبة الآن: {r['pendingDraw2']}")
        r["turn"] = next_index(r)
        return

    # +4 (stack)
    if card["n"] == "+4":
        r["pendingDraw4"] = int(r.get("pendingDraw4", 0)) + 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"العقوبة الآن: اسحب {r['pendingDraw4']} أو رد +4 / تخطي / عكس بنفس اللون")
        r["turn"] = next_index(r)
        return

    # دفاع ضد +4
    if r.get("pendingDraw4", 0) > 0 and card["n"] == "عكس":
        r["direction"] *= -1
        r["log"].insert(0, "تم عكس عقوبة +4")
        r["turn"] = next_index(r)
        return

    if r.get("pendingDraw4", 0) > 0 and card["n"] == "تخطي":
        r["log"].insert(0, "تم تمرير عقوبة +4")
        r["turn"] = next_index(r)
        return

    # عكس / تخطي
    if card["n"] in ["عكس", "تخطي"]:

        # لاعبين فقط
        if len(r["players"]) == 2:
            current = r["turn"]

            if card["n"] == "عكس":
                r["direction"] *= -1
                r["log"].insert(0, "عكس: نفس اللاعب يلعب")
            else:
                r["log"].insert(0, "تخطي: نفس اللاعب يلعب")

            r["turn"] = current
            return

        # أكثر من لاعبين
        if card["n"] == "عكس":
            r["direction"] *= -1
            r["log"].insert(0, "عكس: اللاعب التالي يرد أو يسحب")
        else:
            r["log"].insert(0, "تخطي: اللاعب التالي يرد أو يسحب")

        r["pendingDraw2"] = 2
        r["turn"] = next_index(r)
        return

    # كرت عادي
    r["pendingDraw2"] = 0
    r["turn"] = next_index(r)
def cancel_timer(r):
    t = r.get("timer")
    if t:
        try:
            t.cancel()
        except Exception:
            pass
        r["timer"] = None

def handle_timeout(room):
    r = rooms.get(room)
    if not r:
        return

    idx = r["turn"]

    amount4 = int(r.get("pendingDraw4", 0) or 0)
    amount2 = int(r.get("pendingDraw2", 0) or 0)

    if amount4 > 0:
        total = amount4 + 1
        draw_to(r, idx, total)
        r["pendingDraw4"] = 0
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته ⏱️ وسحب {total}")

    elif amount2 > 0:
        total = amount2 + 1
        draw_to(r, idx, total)
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته ⏱️ وسحب {total}")

    else:
        draw_to(r, idx, 1)
        r["log"].insert(0, f"{r['players'][idx]['name']} انتهى وقته ⏱️ وسحب كرت عقوبة")

    r["turn"] = next_index(r)
    start_timer(room)
    send_state(room)

def start_timer(room):
    r = rooms.get(room)
    if not r:
        return

    old_timer = r.get("timer")
    if old_timer:
        try:
            old_timer.cancel()
        except Exception:
            pass

    r["timeLeft"] = r.get("timeLimit", 30)
    send_state(room)

    def tick():
        rr = rooms.get(room)
        if not rr or not rr.get("started"):
            return

        rr["timeLeft"] = max(0, rr.get("timeLeft", 0) - 1)

        # مهم جداً: تحديث الواجهة كل ثانية
        send_state(room)

        if rr["timeLeft"] <= 0:
            handle_timeout(room)
            send_state(room)
            return

        rr["timer"] = threading.Timer(1, tick)
        rr["timer"].daemon = True
        rr["timer"].start()

    r["timer"] = threading.Timer(1, tick)
    r["timer"].daemon = True
    r["timer"].start()
@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception:
        # Fallback for Render deploys where templates/ was accidentally removed
        return send_file("index.html")

@socketio.on("kick_player")
def on_kick_player(data):
    room = data.get("room")
    host_id = data.get("hostId")
    target_id = data.get("targetId")

    if room not in rooms:
        return

    r = rooms[room]

    # فقط صاحب الغرفة يطرد
    if r.get("host") != host_id:
        emit("error_msg", "فقط قائد الغرفة يقدر يطرد")
        return

    idx = find_player(room, target_id)
    if idx < 0:
        return

    name = r["players"][idx]["name"]
    r["players"].pop(idx)

    if r["turn"] >= len(r["players"]):
        r["turn"] = 0

    r["log"].insert(0, f"🚫 تم طرد {name} من الغرفة")

    emit("kicked", {"room": room}, room=target_id)
    send_state(room)
@socketio.on("join")
def on_join(data):
    room = (data.get("room") or "ROOM1").strip().upper()
    name = (data.get("name") or "لاعب").strip()[:18]
    mode = data.get("mode", "solo")
    team_mode = data.get("teamMode", "auto")
    team_count = max(2, min(3, int(data.get("teamCount", 2) or 2)))
    selected_team = data.get("team", "A")

    if room not in rooms:
        rooms[room] = {
            "players": [],
            "deck": [],
            "discard": [],
            "turn": 0,
            "direction": 1,
            "color": None,
            "started": False,
            "log": [],
            "mode": mode,
            "teamMode": team_mode,
            "teamCount": team_count,
            "pendingDraw4": 0,
            "pendingDraw2": 0,
            "timeLimit": 30,
            "timeLeft": 0,
            "timer": None,
            "host": None
        }

    r = rooms[room]

    if r["started"]:
        emit("error_msg", "اللعبة بدأت، انتظر الجولة القادمة")
        return

    if len(r["players"]) >= 6:
        emit("error_msg", "الغرفة ممتلئة، الحد 6 لاعبين")
        return

    pid = str(uuid.uuid4())

    if len(r["players"]) == 0:
        r["mode"] = mode
        r["teamMode"] = team_mode
        r["teamCount"] = team_count
        r["host"] = pid

    team = None
    if r.get("mode") == "teams":
        if r.get("teamMode") == "manual":
            allowed = TEAM_ORDER[:r.get("teamCount", 2)]
            team = selected_team if selected_team in allowed else allowed[0]
        else:
            team = assign_auto_team(r)

    join_room(room)

    r["players"].append({
        "id": pid,
        "sid": request.sid,
        "name": name,
        "team": team,
        "hand": [],
        "last": False,
        "wins": 0,
        "score": 0
    })

    r["log"].insert(0, f"{name} دخل الغرفة" + (f" - {TEAM_NAMES.get(team, team)}" if team else ""))

    emit("joined", {"room": room, "playerId": pid})
    send_state(room)
@socketio.on("chat")
def on_chat(data):
    room = data.get("room")
    player_id = data.get("playerId")
    text = (data.get("text") or "").strip()

    if room not in rooms or not text:
        return

    r = rooms[room]
    idx = find_player(room, player_id)
    if idx < 0:
        return

    name = r["players"][idx]["name"]
    r["log"].insert(0, f"💬 {name}: {text[:120]}")

    send_state(room)

@socketio.on("change_team")
def on_change_team(data):
    room = data.get("room")
    player_id = data.get("playerId")
    team = data.get("team")
    if room not in rooms:
        return
    r = rooms[room]
    if r["started"]:
        emit("error_msg", "لا يمكن تغيير الفريق بعد البداية")
        return
    idx = find_player(room, player_id)
    allowed = TEAM_ORDER[:r.get("teamCount", 2)]
    if idx >= 0 and team in allowed and r.get("mode") == "teams":
        r["players"][idx]["team"] = team
        r["log"].insert(0, f"{r['players'][idx]['name']} انتقل إلى {TEAM_NAMES.get(team, team)}")
    send_state(room)

@socketio.on("start")
def on_start(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return

    r = rooms[room]

    if r.get("host") != player_id:
        emit("error_msg", "فقط صاحب الغرفة يقدر يبدأ اللعبة ويحدد الوقت")
        return

    if len(r["players"]) < 2:
        emit("error_msg", "لازم لاعبين على الأقل")
        return

    try:
        limit = int(data.get("timeLimit", r.get("timeLimit", 30)) or 30)
    except Exception:
        limit = 30

    r["timeLimit"] = max(5, min(180, limit))
    r["deck"] = build_deck()
    r["discard"] = []
    r["direction"] = 1
    r["started"] = True
    r["color"] = None
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    r["log"] = ["بدأت اللعبة"]

    for p in r["players"]:
        p["hand"] = [r["deck"].pop() for _ in range(7)]
        p["last"] = False

    first = r["deck"].pop()

    while first["c"] == "black" and first["n"] == "لون":
        r["deck"].insert(0, first)
        random.shuffle(r["deck"])
        first = r["deck"].pop()

    r["discard"].append(first)

    if first["c"] == "black":
        r["color"] = random.choice(COLORS)
    else:
        r["color"] = first["c"]

    if first["n"] == "+2":
        r["pendingDraw2"] = 2
        r["log"].insert(0, "🔥 بداية: +2 — اللاعب الأول يرد أو يسحب")

    elif first["n"] == "+4":
        r["pendingDraw4"] = 4
        r["pendingDraw2"] = 0
        r["log"].insert(0, f"🔥 بداية: +4 — اللون {r['color']}")

    host_idx = next((i for i, p in enumerate(r["players"]) if p["id"] == r["host"]), 0)
    r["turn"] = host_idx

    start_timer(room)
    send_state(room)

@socketio.on("play")
def on_play(data):
    room = data.get("room")
    player_id = data.get("playerId")
    index = int(data.get("index", -1))
    chosen_color = data.get("color")

    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)

    if idx < 0:
        emit("error_msg", "اللاعب غير موجود")
        return
    if not r["started"]:
        emit("error_msg", "اللعبة لم تبدأ")
        return
    if idx != r["turn"]:
        emit("error_msg", "مو دورك")
        return

    p = r["players"][idx]
    if index < 0 or index >= len(p["hand"]):
        emit("error_msg", "الكرت غير موجود")
        return

    card = p["hand"][index]

    if not is_allowed(r, card):
        if r.get("pendingDraw4", 0) > 0:
            emit("error_msg", "عليك +4: مسموح +4 أو عكس/تخطي بنفس اللون المطلوب، أو اسحب العقوبة")
        elif r.get("pendingDraw2", 0) > 0:
            emit("error_msg", "عليك رد عكس/تخطي بنفس اللون أو اضغط اسحب لتسحب كرتين")
        else:
            emit("error_msg", "هذا الكرت ما ينفع")
        return

    # play
    p["hand"].pop(index)
    r["discard"].append(card)

    if card["c"] == "black":
        if not chosen_color or chosen_color not in COLORS:
            emit("error_msg", "اختر لون")
            # put card back
            p["hand"].insert(index, card)
            r["discard"].pop()
            return
        r["color"] = chosen_color
    else:
        r["color"] = card["c"]

    r["log"].insert(0, f"{p['name']} رمى {card['n']}")

    # win
    if len(p["hand"]) == 0:
        winner = p
        winner["wins"] = winner.get("wins", 0) + 1
        winner["score"] = max(0, winner.get("score", 0) - 10)

        for i, pp in enumerate(r["players"]):
            if i == idx:
                continue

            add_score = sum(card_points(card) for card in pp["hand"])
            pp["score"] = pp.get("score", 0) + add_score
            r["log"].insert(0, f"📊 {pp['name']} انضاف عليه {add_score} نقطة — المجموع {pp['score']}")

        r["started"] = False
        cancel_timer(r)

        if r.get("mode") == "teams" and winner.get("team"):
            r["log"].insert(0, f"🏆 فاز {TEAM_NAMES.get(winner['team'], winner['team'])} بسبب {winner['name']} وخصم 10 نقاط")
        else:
            r["log"].insert(0, f"🏆 فاز {winner['name']} وخصم 10 نقاط")

        losers = [pp for pp in r["players"] if pp.get("score", 0) >= 500]
        if losers:
            for loser in losers:
                r["log"].insert(0, f"💀 {loser['name']} وصل 500 نقطة وخسر اللعبة")
            r["gameOver"] = True

        send_state(room)
        return

    apply_effect(r, card)

    for pp in r["players"]:
        if len(pp["hand"]) != 1:
            pp["last"] = False

    start_timer(room)
    send_state(room)
@socketio.on("draw")
def on_draw(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)

    if idx < 0:
        emit("error_msg", "اللاعب غير موجود")
        return
    if not r["started"]:
        emit("error_msg", "اللعبة لم تبدأ")
        return
    if idx != r["turn"]:
        emit("error_msg", "مو دورك")
        return

    amount4 = int(r.get("pendingDraw4", 0) or 0)
    amount2 = int(r.get("pendingDraw2", 0) or 0)
    if amount4 > 0:
        draw_to(r, idx, amount4)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب عقوبة {amount4}")
        r["pendingDraw4"] = 0

    elif amount2 > 0:
        draw_to(r, idx, amount2)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب عقوبة +2 عدد {amount2}")
        r["pendingDraw2"] = 0

    else:
        draw_to(r, idx, 1)
        r["log"].insert(0, f"{r['players'][idx]['name']} سحب كرت")
    r["turn"] = next_index(r)
    start_timer(room)
    send_state(room)

@socketio.on("last_card")
def on_last_card(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)
    if idx >= 0 and len(r["players"][idx]["hand"]) == 1:
        r["players"][idx]["last"] = True
        r["log"].insert(0, f"{r['players'][idx]['name']} قال: كرت أخير")
    else:
        emit("error_msg", "تقدر تضغط كرت أخير لما يبقى عندك كرت واحد")
    send_state(room)


@socketio.on("leave_room")
def on_leave_room(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    idx = find_player(room, player_id)
    if idx < 0:
        return
    name = r["players"][idx]["name"]
    r["players"].pop(idx)
    if not r["players"]:
        cancel_timer(r)
        del rooms[room]
        emit("left_room", {"ok": True})
        return
    # إذا اللي خرج هو صاحب الغرفة
    if r.get("host") == player_id:
        new_host = r["players"][0]
        r["host"] = new_host["id"]
        r["log"].insert(0, f"{new_host['name']} أصبح قائد الغرفة 👑")
    if r["turn"] >= len(r["players"]):
        r["turn"] = 0
    r["log"].insert(0, f"{name} خرج من الغرفة")
    emit("left_room", {"ok": True})
    send_state(room)

@socketio.on("end_game")
def on_end_game(data):
    room = data.get("room")
    player_id = data.get("playerId")
    if room not in rooms:
        return
    r = rooms[room]
    if r.get("host") != player_id:
        emit("error_msg", "فقط صاحب الغرفة يقدر ينهي اللعبة")
        return
    r["started"] = False
    r["pendingDraw4"] = 0
    r["pendingDraw2"] = 0
    cancel_timer(r)
    r["log"].insert(0, "تم إنهاء اللعبة بواسطة صاحب الغرفة")
    send_state(room)

@socketio.on("disconnect")
def on_disconnect():
    for room, r in list(rooms.items()):
        before = len(r["players"])
        r["players"] = [p for p in r["players"] if p["sid"] != request.sid]
        if len(r["players"]) != before:
            if not r["players"]:
                cancel_timer(r)
                del rooms[room]
            else:
                if r["turn"] >= len(r["players"]):
                    r["turn"] = 0
                r["log"].insert(0, "لاعب خرج من الغرفة")
                send_state(room)
            break

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
