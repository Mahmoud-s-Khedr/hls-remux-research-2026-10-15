const fs=require('fs'),path=require('path');
const {chromium}=require('/home/mk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'../../outputs/hls-scaling');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/mk/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args:['--autoplay-policy=no-user-gesture-required']});
 const data=JSON.parse(fs.readFileSync(path.join(root,'results.json')));
 const output=path.join(root,'browser-validation.json');
 const r=fs.existsSync(output)?JSON.parse(fs.readFileSync(output)):{browser:await browser.version(),player:'hls.js 1.6.13',method:'Normal-speed startup, middle seek, end seek and completion; not full real-time viewing of every long asset',tests:[]};
 const existing=new Map(r.tests.map(x=>[x.id,x]));
 const jobs=data.durations.flatMap(d=>d.cases.filter(c=>c.validation?.passed&&!existing.has(c.id)).map(c=>({id:c.id,playlist:c.playlist})));
 async function worker(){
  const page=await browser.newPage();await page.goto('http://127.0.0.1:8765/work/player-test.html');
  while(jobs.length){
   const job=jobs.shift();
   const result=await page.evaluate(async(url)=>{
    const v=document.querySelector('video'),errors=[],events=[];let hls,stage='loading';
    const delay=t=>new Promise(r=>setTimeout(r,t));
    async function until(test,ms){const end=Date.now()+ms;while(!test()){if(Date.now()>end)throw Error('Timeout at '+stage);await delay(50);}}
    async function seek(t){await new Promise((res,rej)=>{const timer=setTimeout(()=>rej(Error('Seek timeout at '+t)),12000);v.addEventListener('seeked',()=>{clearTimeout(timer);res();},{once:true});v.currentTime=t;});await until(()=>v.readyState>=2,12000);}
    try{
     hls=new Hls({maxBufferLength:20,maxMaxBufferLength:40,maxBufferSize:32*1024*1024});
     hls.on(Hls.Events.ERROR,(_,d)=>errors.push({stage,type:d.type,details:d.details,fatal:d.fatal}));
     hls.loadSource(url);hls.attachMedia(v);v.muted=true;v.playbackRate=1;
     await until(()=>Number.isFinite(v.duration)&&v.readyState>=2,20000);
     const duration=v.duration;
     stage='startup';await seek(.1);await v.play();await delay(1000);v.pause();events.push({stage,time:v.currentTime});
     stage='middle';await seek(duration/2);await v.play();await delay(1000);v.pause();events.push({stage,time:v.currentTime});
     stage='end';await seek(Math.max(.1,duration-3));await v.play();
     await until(()=>v.ended||v.error||errors.some(e=>e.fatal),12000);
     events.push({stage,time:v.currentTime});
     const q=v.getVideoPlaybackQuality();
     const result={passed:v.ended&&!v.error&&!errors.length&&v.videoWidth===1920&&v.videoHeight===1080,
      ended:v.ended,duration,currentTime:v.currentTime,width:v.videoWidth,height:v.videoHeight,
      events,errors,mediaError:v.error?.message||null,renderCounters:{total:q.totalVideoFrames,dropped:q.droppedVideoFrames}};
     return result;
    }catch(e){return{passed:false,error:String(e),stage,events,errors};}
    finally{if(hls)hls.destroy();v.pause();v.removeAttribute('src');v.load();}
   },'/outputs/hls-scaling/'+job.playlist);
   r.tests.push({...job,...result});fs.writeFileSync(output,JSON.stringify(r,null,2));
   console.log('BROWSER',job.id,result.passed,result.error||'',JSON.stringify(result.errors));
  }
  await page.close();
 }
 await Promise.all(Array.from({length:4},worker));await browser.close();
 console.log('BROWSER COMPLETE',r.tests.length,r.tests.filter(t=>t.passed).length);
})().catch(e=>{console.error(e);process.exitCode=1;});
