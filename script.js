const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);

function clock(){ $("#clock").textContent=new Date().toLocaleTimeString([], {hour12:false}); }
clock(); setInterval(clock,1000);
async function loadWeather(){
  const el=$("#weatherTop");
  if(!el) return;
  const set=(t)=>{el.textContent=t;};
  const codeMap={0:"CLEAR",1:"MAINLY CLEAR",2:"PARTLY CLOUDY",3:"CLOUDY",45:"FOG",48:"FOG",51:"DRIZZLE",53:"DRIZZLE",55:"DRIZZLE",61:"RAIN",63:"RAIN",65:"HEAVY RAIN",71:"SNOW",73:"SNOW",75:"HEAVY SNOW",80:"SHOWERS",81:"SHOWERS",82:"HEAVY SHOWERS",95:"THUNDER",96:"THUNDER",99:"THUNDER"};
  const show=async(latitude,longitude,label)=>{
    const url=`https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto`;
    const r=await fetch(url,{cache:"no-store"});
    if(!r.ok) throw new Error("weather");
    const d=await r.json(); const c=d.current||{};
    const temp=Number.isFinite(Number(c.temperature_2m))?Math.round(c.temperature_2m):"--";
    const condition=codeMap[c.weather_code]||"LIVE";
    const wind=Number.isFinite(Number(c.wind_speed_10m))?Math.round(c.wind_speed_10m):null;
    set(`${temp}°C · ${condition}${wind!==null?` · ${wind} KM/H`:""}`);
    const mod=$("#weatherModule");
    if(mod) mod.title=`LIVE WEATHER · ${label}`;
  };

  // Try the browser's approximate location first. If permission is denied,
  // keep the telemetry alive with a Kerala fallback instead of showing LOCATION OFF.
  if(navigator.geolocation){
    navigator.geolocation.getCurrentPosition(
      pos=>show(pos.coords.latitude,pos.coords.longitude,"CURRENT LOCATION").catch(()=>show(11.8745,75.3704,"KANNUR / KERALA").catch(()=>set("WEATHER OFFLINE"))),
      ()=>show(11.8745,75.3704,"KANNUR / KERALA").catch(()=>set("WEATHER OFFLINE")),
      {enableHighAccuracy:false,timeout:5000,maximumAge:900000}
    );
  }else{
    show(11.8745,75.3704,"KANNUR / KERALA").catch(()=>set("WEATHER OFFLINE"));
  }
}

loadWeather();
setInterval(loadWeather,600000);

/* Instagram DM HUD — messages arrive through the secure Python webhook. */
const igMessagesEl=$("#igMessages"), igUnreadEl=$("#igUnread"), igStatusText=$("#igConnectionText"), igDot=$("#igConnectionDot");
function escHTML(value){
  return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function renderInstagramMessages(items=[]){
  if(!igMessagesEl)return;
  const list=Array.isArray(items)?items:[];
  igUnreadEl.textContent=list.filter(x=>x.unread).length;
  if(!list.length){
    igMessagesEl.innerHTML='<div class="ig-empty">NO INSTAGRAM MESSAGES LOADED</div>';
    return;
  }
  igMessagesEl.innerHTML=list.slice(-20).reverse().map(m=>{
    const name=escHTML(m.sender_name||m.sender_id||"INSTAGRAM USER");
    const text=escHTML(m.text||"[NON-TEXT MESSAGE]");
    const when=escHTML(m.time_display||"LIVE");
    return `<article class="ig-msg ${m.unread?"unread":""}"><div class="ig-msg-head"><b>${name}</b><span>${when}</span></div><div class="ig-msg-text">${text}</div></article>`;
  }).join("");
}
async function loadInstagramDMs(){
  if(!igMessagesEl)return;
  try{
    const r=await fetch("/api/instagram/status",{cache:"no-store"});
    const s=await r.json();
    if(s.connected){
      igStatusText.textContent="META WEBHOOK CONNECTED";
      igDot.className="online";
    }else if(s.webhook_ready){
      igStatusText.textContent="WEBHOOK READY · AWAITING DMS";
      igDot.className="warn";
    }else{
      igStatusText.textContent="META API NOT CONNECTED";
      igDot.className="";
    }
    renderInstagramMessages(s.messages||[]);
  }catch(e){
    igStatusText.textContent="INSTAGRAM SERVICE OFFLINE";
    igDot.className="";
  }
}
loadInstagramDMs();
setInterval(loadInstagramDMs,15000);
$("#igRefresh")?.addEventListener("click",loadInstagramDMs);
$(".ig-notifier")?.addEventListener("click",()=>setTimeout(loadInstagramDMs,250));

function runLoader(){
  const loader=$("#nexoraLoader"), bar=$("#loaderBar"), pct=$("#loaderPercent"), log=$("#loaderLog");
  if(!loader) return;
  const steps=[[18,"CORE POWER ONLINE"],[38,"NEURAL NETWORK INITIALIZED"],[58,"VOICE INTERFACE READY"],[78,"MULTI-AI ROUTER READY"],[94,"SECURE API GATEWAY READY"],[100,"NEXORA ONLINE"]];
  let i=0;
  const timer=setInterval(()=>{
    const [n,t]=steps[i++]; if(bar)bar.style.width=n+"%"; if(pct)pct.textContent=n+"%"; if(log)log.textContent="BOOT SEQUENCE // "+t;
    if(i>=steps.length){clearInterval(timer);setTimeout(()=>loader.classList.add("hidden"),350);}
  },170);
}
runLoader();



const bars=$("#bars");
[35,50,42,70,55,82,45,66,52,76,43,90,65,80].forEach((h,i)=>{
  const b=document.createElement("i"); b.style.height=h+"%"; b.style.animationDelay=(i*.05)+"s"; bars.appendChild(b);
});
const waveform=$("#waveform");
for(let i=0;i<34;i++){const b=document.createElement("i");b.style.height=(15+(i*17)%32)+"px";b.style.animationDelay=(i*.035)+"s";waveform.appendChild(b);}

const logTexts=["SYSTEM INTEGRITY CHECK COMPLETE","AI CORE STABLE AT 98.4%","NEURAL NETWORK INITIALIZED","MULTI-AI ROUTER READY","AWAITING USER INPUT...","VOICE INTERFACE STANDBY","SECURE API GATEWAY READY"];
const logs=$("#logs");
logTexts.forEach((x,i)=>{const p=document.createElement("p");p.innerHTML=`<time>[12:45:${String(i*9+1).padStart(2,"0")}]</time>${x}`;logs.appendChild(p);});

const overlay=$("#chatOverlay"), chatMessages=$("#chatMessages"), chatInput=$("#chatInput"), quickInput=$("#quickInput");
const modelSelect=$("#modelSelect");
function openChat(text=""){overlay.classList.add("open");overlay.setAttribute("aria-hidden","false");if(text){chatInput.value=text}setTimeout(()=>chatInput.focus(),80)}
function closeChat(){}
// Keep the right-side chat HUD visible from the initial page load.
$("#openChat").onclick=()=>openChat();

let history=[];
let lastReply="";
let voiceEnabled=true;
let speechWaveTimer=null;
const thinkingIndicator=$("#thinkingIndicator");
const speakBtn=$("#speakBtn");
const coreSection=$(".core-section");
const coreOrb=$(".core");

function setSpeaking(active){
  document.body.classList.toggle("voice-speaking",active);
  if(coreSection) coreSection.setAttribute("data-speaking",active?"true":"false");
  if(speechWaveTimer){clearInterval(speechWaveTimer);speechWaveTimer=null;}
  if(active){
    speechWaveTimer=setInterval(()=>{
      if(!waveform) return;
      waveform.querySelectorAll("i").forEach((bar,i)=>{
        const base=12+Math.random()*34;
        const pulse=(Math.sin(Date.now()/95+i*.65)+1)*8;
        bar.style.height=Math.max(7,Math.min(48,base+pulse))+"px";
      });
    },90);
  }else if(waveform){
    waveform.querySelectorAll("i").forEach((bar,i)=>{bar.style.height=(15+(i*17)%32)+"px";});
  }
}

function speak(text){
  if(!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  setSpeaking(false);
  const clean=text.replace(/```[\s\S]*?```/g," code block omitted ").replace(/[#*_`>]/g,"").replace(/\s+/g," ").trim();
  if(!clean)return;
  const u=new SpeechSynthesisUtterance(clean);
  u.rate=1.20;
  u.pitch=1.02;
  u.volume=1;
  u.lang="en-US";
  const voices=speechSynthesis.getVoices();
  const preferred=voices.find(v=>/Google US English|Microsoft Aria|Microsoft Jenny|Samantha/i.test(v.name));
  if(preferred)u.voice=preferred;
  u.onstart=()=>setSpeaking(true);
  u.onboundary=()=>{
    document.body.classList.remove("voice-beat");
    void document.body.offsetWidth;
    document.body.classList.add("voice-beat");
  };
  u.onend=()=>{setSpeaking(false);document.body.classList.remove("voice-beat");};
  u.onerror=()=>{setSpeaking(false);document.body.classList.remove("voice-beat");};
  speechSynthesis.speak(u);
}
if(speakBtn)speakBtn.onclick=()=>{if(lastReply)speak(lastReply)};
if(speakBtn)speakBtn.onclick=()=>{if(lastReply)speak(lastReply)};

function addMessage(role,text,provider="NEXORA"){
  const wrap=document.createElement("div");wrap.className="chat-message "+role;
  const safe=text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  wrap.innerHTML=`<div class="chat-avatar">${role==="ai"?"✦":"U"}</div><div><small>${role==="ai"?provider:"YOU"}</small><p>${safe.replace(/\n/g,"<br>")}</p>${role==="ai"?'<div class="message-actions"><button type="button" class="copy-reply">COPY</button><button type="button" class="speak-reply">SPEAK</button></div>':""}</div>`;
  chatMessages.appendChild(wrap);chatMessages.scrollTop=chatMessages.scrollHeight;
  if(role==="ai"){
    const copy=wrap.querySelector(".copy-reply");
    const sp=wrap.querySelector(".speak-reply");
    copy.onclick=()=>navigator.clipboard?.writeText(text);
    sp.onclick=()=>speak(text);
  }
}


function addLimitMessage(message, upgradeUrl){
  const wrap=document.createElement("div");
  wrap.className="quota-card";
  wrap.innerHTML=`<div class="quota-icon">!</div><div class="quota-content"><small>GEMINI // LIMIT REACHED</small><h3>API QUOTA REACHED</h3><p>${message||"Your Gemini API free-tier quota has been reached."}</p><div class="quota-actions"><a href="${upgradeUrl||"https://aistudio.google.com/billing"}" target="_blank" rel="noopener noreferrer">UPGRADE SUBSCRIPTION</a><button type="button" class="quota-close">CLOSE</button></div></div>`;
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop=chatMessages.scrollHeight;
  wrap.querySelector(".quota-close").onclick=()=>wrap.remove();
}

function setBusy(busy){
  document.body.classList.toggle("ai-thinking",busy);
  const sendBtn=document.querySelector("#chatForm button[type=submit]");
  if(sendBtn)sendBtn.disabled=busy;
  chatInput.placeholder=busy?"NEXORA IS THINKING...":"Transmit command...";
  if(thinkingIndicator){
    thinkingIndicator.hidden=!busy;
    if(busy){
      // Keep the thinking HUD directly UNDER the user's question.
      chatMessages.appendChild(thinkingIndicator);
      chatMessages.scrollTop=chatMessages.scrollHeight;
    }
  }
}

async function send(text){
  if(!text.trim())return;
  document.querySelector(".welcome")?.remove();
  addMessage("user",text);
  history.push({role:"user",content:text});
  chatInput.value=""; if(quickInput)quickInput.value="";
  setBusy(true);
  try{
    const response=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,provider:modelSelect?.value||"auto",history})});
    const data=await response.json();
    if(!response.ok){
      if(data.code==="GEMINI_QUOTA_REACHED"){
        addLimitMessage(data.error, data.upgrade_url);
        return;
      }
      throw new Error(data.error||"NEXORA backend error");
    }
    lastReply=data.reply||"";
    history.push({role:"assistant",content:lastReply});
    addMessage("ai",lastReply,data.provider_label||data.provider||"NEXORA");
    if(voiceEnabled)speak(lastReply);
  }catch(err){addMessage("ai",`SYSTEM ERROR: ${err.message}`,"SYSTEM");}
  finally{setBusy(false)}
}

function startVoice(){
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognition){chatInput.placeholder="Voice input is not supported in this browser";return;}
  const r=new SpeechRecognition();r.lang="en-US";r.interimResults=true;r.continuous=false;
  r.onstart=()=>{chatInput.placeholder="LISTENING...";document.body.classList.add("voice-listening")};
  r.onresult=e=>{let t="";for(const result of e.results)t+=result[0].transcript;chatInput.value=t;if(e.results[e.results.length-1].isFinal){chatInput.placeholder="Transmit command...";send(t)}};
  r.onerror=()=>chatInput.placeholder="Voice unavailable — type your command";
  r.onend=()=>{chatInput.placeholder="Transmit command...";document.body.classList.remove("voice-listening")};
  r.start();
}

$("#chatForm").addEventListener("submit",e=>{e.preventDefault();send(chatInput.value)});
$("#quickForm").addEventListener("submit",e=>{e.preventDefault();if(quickInput.value.trim()){openChat();chatInput.value=quickInput.value;send(quickInput.value)}});
$$(".quick-actions button").forEach(b=>b.addEventListener("click",()=>openChat(b.dataset.prompt)));

$("#voiceBtn").addEventListener("click",startVoice);
