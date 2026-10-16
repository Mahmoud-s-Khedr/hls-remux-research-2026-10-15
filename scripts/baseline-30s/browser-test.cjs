const {chromium} = require('/home/mk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
const workspace=process.env.HLS_BENCHMARK_ROOT||path.resolve(__dirname,'..');
const root=path.join(workspace,'outputs/hls-benchmark');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/mk/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args:['--autoplay-policy=no-user-gesture-required']});
 const source=JSON.parse(fs.readFileSync(path.join(root,'results.json')));
 const resultPath=path.join(root,'browser-validation.json');
 const prior=fs.existsSync(resultPath)?JSON.parse(fs.readFileSync(resultPath)):null;
 const checks=prior?.playbackRate===1?prior:{browser:await browser.version(),player:'hls.js 1.6.13',playbackRate:1,preload:true,tests:[]};
 const jobs=[];
 for(const f of source.fixtures)for(const[k,d]of Object.entries(f.outputs)){
  if(!d.warmup_ok)continue;
  if(process.env.SKIP_KEYS?.split(',').includes(f.key))continue;
  if(process.env.ONLY_KEYS&&!process.env.ONLY_KEYS.split(',').includes(f.key))continue;
  jobs.push({container:f.key,kind:k,playlist:d.playlist});
 }
 async function worker(){
  const page=await browser.newPage();
  await page.goto('http://127.0.0.1:8765/work/player-test.html');
  while(jobs.length){
   const job=jobs.shift();
   const result=await page.evaluate(async(url)=>{
    const video=document.querySelector('video'),errors=[],events=[];
    let hls,stage='loading';
    const delay=ms=>new Promise(r=>setTimeout(r,ms));
    async function until(test,ms){let end=Date.now()+ms;while(!test()){if(Date.now()>end)throw Error('Timeout at '+stage);await delay(100);}}
    async function seek(t){await new Promise((res,rej)=>{const timer=setTimeout(()=>rej(Error('Seek timeout')),8000);video.addEventListener('seeked',()=>{clearTimeout(timer);res();},{once:true});video.currentTime=t;});}
    try{
     hls=new Hls({maxBufferLength:60,maxMaxBufferLength:120,maxBufferSize:128*1024*1024});
     hls.on(Hls.Events.ERROR,(_,d)=>errors.push({stage,type:d.type,details:d.details,fatal:d.fatal}));
     hls.loadSource(url);hls.attachMedia(video);video.muted=true;video.playbackRate=1;
     await until(()=>Number.isFinite(video.duration)&&video.buffered.length&&video.buffered.end(video.buffered.length-1)>=video.duration-0.15,25000);
     events.push('fully-buffered');
     stage='seeking';await seek(18);events.push('seeked-to-18s');await seek(0.1);events.push('seeked-to-start');
     stage='playing';await video.play();events.push('playing');
     await until(()=>video.ended||video.error||errors.some(e=>e.fatal),40000);
     const q=video.getVideoPlaybackQuality();
     const result={ended:video.ended,currentTime:video.currentTime,duration:video.duration,width:video.videoWidth,height:video.videoHeight,
      quality:{totalVideoFrames:q.totalVideoFrames,droppedVideoFrames:q.droppedVideoFrames},events,errors,mediaError:video.error?.message||null};
     result.passed=result.ended&&result.width===1920&&result.height===1080&&!errors.length&&!video.error;
     return result;
    }catch(e){return{passed:false,error:String(e),stage,events,errors};}
    finally{if(hls)hls.destroy();video.pause();video.removeAttribute('src');video.load();}
   },'/outputs/hls-benchmark/'+job.playlist);
   checks.tests=checks.tests.filter(t=>!(t.container===job.container&&t.kind===job.kind));
   checks.tests.push({...job,...result});
   fs.writeFileSync(resultPath,JSON.stringify(checks,null,2));
   console.log(job.container,job.kind,result.passed,result.error||'',JSON.stringify(result.errors));
  }
  await page.close();
 }
 await Promise.all(Array.from({length:4},worker));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
