"use strict";
const $=id=>document.getElementById(id);
const token=document.querySelector('meta[name="metro-token"]').content;
const writes=new Set(['stationAdd','stationUpdate','stationDelete','lineAdd','lineUpdate','lineDelete','lineInsert','lineRemove','membershipUpdate']);
const groups={
 stations:{title:'站点与出口',sub:'查找车站，查看所属线路、出口和地标。',actions:[['stations','查询站点',['match','search']],['stationDetail','站点详情与出口',['station_id']],['stationAdd','新增站点',['name_zh','name_en','district_id','lon_mdeg','lat_mdeg']],['stationUpdate','修改站点',['station_id','name_zh','name_en','district_id','lon_mdeg','lat_mdeg']],['stationDelete','删除站点',['station_id']],['landmarks','查找地标',['search']]]},
 lines:{title:'线路编排',sub:'维护线路与站序，让每一站各归其位。',actions:[['lines','全部线路',[]],['lineStations','查看线路站序',['line_id']],['lineAdd','新增线路',['name_zh','name_en']],['lineUpdate','修改线路',['line_id','name_zh','name_en']],['lineDelete','删除线路',['line_id']],['lineInsert','指定位置插入站点',['line_id','position','station_ids','status','opening_year','first_train','last_train']],['lineRemove','移出线路',['line_id','station_id']],['membershipUpdate','更新线路站点属性',['line_id','station_id','status','opening_year','first_train','last_train']]]},
 routes:{title:'路线查询',sub:'选择出发与到达地点，探索线路连接。',actions:[['route','两站之间',['start','end','mode','planned']],['landmarkRoute','两地标之间',['start_landmark','end_landmark','mode','planned']],['fare','查询票价',['start','end']]]},
 queries:{title:'数据核验',sub:'使用项目规定的七类查询，核对数据准确性。',actions:[['q1','Q1 · 物理站点数量',[]],['q2','Q2 · 线路数量',[]],['q3','Q3 · 各区运营站数量',[]],['q4','Q4 · 线路开通年统计',['line_name']],['q5','Q5 · 出口最多站点',['line_name']],['q6','Q6 · 地标前缀',['prefix']],['q7','Q7 · 前后第 n 站',['station_name','line_name','n']]]}
};
const labels={search:'搜索词（可留空）',station_id:'站点',line_id:'线路',name_zh:'中文名称',name_en:'英文名称',district_id:'行政区',lon_mdeg:'经度 × 1000（可空）',lat_mdeg:'纬度 × 1000（可空）',position:'插入位置（从 1 开始）',station_ids:'站点 ID 列表（英文逗号分隔）',status:'运营状态',opening_year:'开通 / 预计开通年',first_train:'首班时间（可空）',last_train:'末班时间（可空）',start:'出发站',end:'到达站',mode:'路径偏好',planned:'网络范围',start_landmark:'起点地标完整名称',end_landmark:'终点地标完整名称',line_name:'线路英文名',station_name:'站点英文名',n:'前后站数 n',prefix:'LIKE 前缀（例如：塘朗%）',station_count:'站点数',line_count:'线路数',district:'行政区',cnt:'数量',opening:'开通年',english_name:'英文站名',chinese_name:'中文站名',exit:'出口',name:'地标名称',neighbor:'邻站',exit_code:'出口',landmark_name:'地标',exit_count:'出口数'};
let current='stations',allStations=[],allLines=[],districts=[],selectedLineId='';
const columnLabels={station_id:'站点编号',line_id:'线路编号',position:'Num（站序）'};
const searchModes = [
 ['all', '全部字段', '罗湖、Luohu、#347、Longgang'],
 ['station_id', '站点编号（精确）', '347 或 #347'],
 ['name_zh', '中文站名（包含）', '罗湖'],
 ['name_en', '英文站名（包含）', 'Luohu'],
 ['district', '行政区（包含）', 'Longgang']
];
const stationInputs = new Map();
function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
async function api(action,params={}){
 const body=new URLSearchParams({action,...params});
 const usePost=writes.has(action)||action==='sqlQuery';
 let response;
 try {
  response=await fetch(usePost?'/api':'/api?'+body.toString(),usePost?{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','X-Metro-Token':token},body}:{});
 } catch {
  throw new Error('无法连接网页服务。请确认程序仍在运行，再重试。');
 }
 const result=await response.json();if(!response.ok)throw new Error(result.error||'请求失败');return result.data;
}
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
function option(select,value,label){const o=element('option',label);o.value=value;select.append(o);}
function actionSpec(){return groups[current].actions.find(a=>a[0]===$('operation').value);}
function operationButton() {
 return $('operation-form').querySelector('button[type=submit]');
}
function stationLabel(station) {
 return `${station.name_zh} · ${station.name_en} · ${station.district} · #${station.station_id}`;
}
function stationMatches(text) {
 const term=text.trim().toLowerCase();
 if(!term)return allStations;
 if(/^#?[0-9]+$/.test(term)) {
  const number=Number(term.replace('#',''));
  return allStations.filter(station=>station.station_id===number);
 }
 const names=allStations.filter(station=>station.name_zh.includes(term)||station.name_en.toLowerCase().includes(term));
 const exact=names.filter(station=>station.name_zh===term||station.name_en.toLowerCase()===term);
 return exact.length?exact:names;
}
function stationFromInput(text,selection,label) {
 if(selection) {
  const station=allStations.find(station=>String(station.station_id)===selection);
  if(station)return station;
 }
 const term=text.trim();
 if(!term)throw new Error(`请输入或选择${label}。`);
 const matches=stationMatches(term);
 if(matches.length===1)return matches[0];
 if(matches.length>1)throw new Error(`“${term}”匹配到 ${matches.length} 个站点。请在候选中按行政区选择，或输入编号。`);
 throw new Error(`找不到站点“${term}”。请检查中英文站名或编号，或刷新站点列表。`);
}
function stationPicker(label,batch) {
 const box=element('fieldset',undefined,'station-picker');
 const input=element('input');
 input.type='text';
 input.placeholder='例如 罗湖、Luohu 或 #347';
 input.autocomplete='off';
 const inputLabel=element('label','输入站名或编号');
 inputLabel.append(input);
 const candidates=element('select');
 const selectLabel=element('label','选择候选站点');
 selectLabel.append(candidates);
 const guidance=element('p','', 'hint');
 guidance.setAttribute('aria-live','polite');
 const queue=[];
 const queueView=element('ol',undefined,'station-queue');
 const refreshCandidates=()=>{
  const term=input.value.trim();
  const multiple=batch&&/[,，、\n]/.test(term);
  const matches=multiple?[]:stationMatches(term);
  candidates.replaceChildren();
  option(candidates,'','请选择站点');
  for(const station of matches)option(candidates,String(station.station_id),stationLabel(station));
  candidates.value='';
  if(multiple) {
   guidance.textContent='将按输入顺序逐个匹配。遇到同名站可改用编号。';
  } else if(!term) {
   guidance.textContent='可直接从候选列表选择。';
  } else if(matches.length===0) {
   guidance.textContent='没有匹配站点，请检查输入。';
  } else if(matches.length===1) {
   guidance.textContent='找到 1 个站点，可直接提交。';
  } else {
   guidance.textContent=`找到 ${matches.length} 个站点，请选择对应行政区和编号。`;
  }
 };
 input.addEventListener('input',refreshCandidates);
 candidates.addEventListener('change',()=>{
  const picked=allStations.find(station=>String(station.station_id)===candidates.value);
  if(picked)guidance.textContent=stationLabel(picked);
 });
 box.append(element('legend',label),inputLabel,selectLabel,guidance);
 refreshCandidates();
 const pending=()=>{
  if(candidates.value)return [stationFromInput(input.value,candidates.value,label)];
  if(!input.value.trim())return [];
  return input.value.split(/[,，、\n]/).map(term=>stationFromInput(term,'',label));
 };
 function unique(stations) {
  if(new Set(stations.map(station=>station.station_id)).size!==stations.length) {
   throw new Error('同一批次中有重复站点，请移除重复项。');
  }
  return stations;
 }
 if(batch) {
  const add=element('button','加入插入列表','quiet');
  add.type='button';
  const renderQueue=()=>{
   queueView.replaceChildren();
   queue.forEach((station,index)=>{
    const item=element('li');
    const remove=element('button','移除','quiet');
    remove.type='button';
    remove.setAttribute('aria-label','从列表移除 '+stationLabel(station));
    remove.addEventListener('click',()=>{queue.splice(index,1);renderQueue();});
    item.append(element('span',stationLabel(station)),remove);
    queueView.append(item);
   });
  };
  add.addEventListener('click',()=>{
   try {
    const additions=pending();
    if(!additions.length)throw new Error('请先输入或选择要插入的站点。');
    unique([...queue,...additions]);
    queue.push(...additions);
    input.value='';
    refreshCandidates();
    renderQueue();
    notice('');
    input.focus();
   } catch(e) { notice(e.message,true); }
  });
  box.append(add,queueView);
 }
 const value=()=>{
  if(!batch)return String(stationFromInput(input.value,candidates.value,label).station_id);
  const stations=unique([...queue,...pending()]);
  if(!stations.length)throw new Error('请至少输入或选择一个要插入的站点。');
  return stations.map(station=>station.station_id).join(',');
 };
 return {box,value};
}
function fields(){
 const [action,title,keys]=actionSpec();$('fields').replaceChildren();
 const submit=operationButton();
 submit.textContent=title;
 submit.classList?.toggle('danger',action.endsWith('Delete'));
 $('operation-title').textContent=writes.has(action)?'编辑条件':'查询条件';
 stationInputs.clear();
 for(const key of keys){
  if(key==='station_ids'||key==='start'||key==='end'||(key==='station_id'&&action!=='stationUpdate')){
   const picker=stationPicker(key==='station_ids'?'要插入的站点':labels[key],key==='station_ids');
   stationInputs.set(key,picker.value);
   $('fields').append(picker.box);
   continue;
  }
  const label=element('label',labels[key]||key);let field;
  if(['match','station_id','line_id','district_id','status','mode','planned','line_name'].includes(key)){
   field=element('select');
   if(key==='match'){
    label.textContent='匹配字段';
    for(const [value,title] of searchModes)option(field,value,title);
   }
   if(key==='station_id')for(const s of allStations)option(field,s.station_id,stationLabel(s));
   if(key==='line_id'){
    for(const l of allLines)option(field,l.line_id,`${l.name_zh} · ${l.name_en} · #${l.line_id}`);
    if(allLines.some(l=>String(l.line_id)===selectedLineId))field.value=selectedLineId;
    field.addEventListener('change',()=>{selectedLineId=field.value;});
   }
   if(key==='line_name')for(const l of allLines)option(field,l.name_en,l.name_en);
   if(key==='district_id')for(const d of districts)option(field,d.district_id,d.name_en);
   if(key==='status'){option(field,'Operation','运营 Operation');option(field,'Construction','在建 Construction');}
   if(key==='mode'){option(field,'stops','最少经过站数');option(field,'transfers','最少换乘，再最少站数');}
   if(key==='planned'){option(field,'false','仅运营网络');option(field,'true','包含在建网络');}
  }else{
   field=element('input');field.type=['position','opening_year','n','lon_mdeg','lat_mdeg'].includes(key)?'number':key.includes('train')?'time':'text';
   if(key==='search'&&action==='stations'){
    const match=$('operation-form').elements.match;
    const setExample=()=>{
     field.placeholder=(searchModes.find(mode=>mode[0]===match.value)||searchModes[0])[2];
    };
    match.addEventListener('change',setExample);
    setExample();
   }
   if(key==='position')field.value='1';if(key==='opening_year')field.value='2026';if(key==='n')field.value='2';
   if(key==='prefix')field.value='塘朗%';if(key==='station_name')field.value='Mawan';
  }
  field.name=key;field.required=!['search','lon_mdeg','lat_mdeg','first_train','last_train'].includes(key);label.append(field);$('fields').append(label);
 }
 const hints={
  stations:'编号精确匹配，站名和行政区支持包含匹配，英文忽略大小写。搜索词留空显示全部站点。',
  stationDetail:'可输入中文站名、英文站名或编号。遇到同名站，请按行政区选择。',
  lineInsert:'按列表顺序插入。可逐个加入，也可用逗号输入多个站名或编号，例如「罗湖, 上屋」。每批共用状态、年份和时刻。',
  stationUpdate:'选择站点后自动填充现有信息。清空坐标会删除坐标值。',
  stationDelete:'删除车站会同时删除出口，并修复相关线路站序。',
  lineRemove:'从线路移出站点后会重排站序，车站资料仍保留。',
  fare:'源 CSV 未提供票价。配置票价矩阵后可查询。',
  landmarkRoute:'在「站点与出口 → 查找地标」中查候选名称，复制完整地标名。',
  q7:'输入英文站名和步数 n，并选择线路。依次返回较小和较大站序方向的邻站，越界显示空值。'
 };
 $('hint').textContent=hints[action]||'';
 if(action==='stationUpdate'){
  const fill=()=>{const s=allStations.find(s=>String(s.station_id)===$('operation-form').elements.station_id.value);if(s)for(const k of ['name_zh','name_en','district_id','lon_mdeg','lat_mdeg'])$('operation-form').elements[k].value=s[k]??'';};
  $('operation-form').elements.station_id.addEventListener('change',fill);fill();
 }
 if(action==='lineUpdate'){
  const fill=()=>{const l=allLines.find(l=>String(l.line_id)===$('operation-form').elements.line_id.value);if(l)for(const k of ['name_zh','name_en'])$('operation-form').elements[k].value=l[k];};
  $('operation-form').elements.line_id.addEventListener('change',fill);fill();
 }
}
function showTable(rows,parent,columns){
 if(!rows.length&&!columns){parent.append(element('p','没有匹配记录。','empty'));return;}
 const table=element('table'),head=element('thead'),hr=element('tr'),body=element('tbody');
 const keys=columns||Object.keys(rows[0]);
 for(const key of keys){
  const heading=element('th',columns?key:columnLabels[key]||labels[key]||key);
  heading.scope='col';
  hr.append(heading);
 }
 head.append(hr);
 for(const result of rows){
  const row=element('tr');
  const values=columns?result:keys.map(key=>result[key]);
  for(const value of values)row.append(element('td',value===null?(columns?'NULL':'空值'):String(value)));
  body.append(row);
 }
 table.append(head,body);parent.append(table);
 if(!rows.length)parent.append(element('p','查询成功，返回 0 行。','empty'));
}
function render(data){
 const target=$('result');target.replaceChildren();
 if(Array.isArray(data)){showTable(data,target);$('result-title').textContent=`查询结果 · ${data.length} 条`;return;}
 $('result-title').textContent='查询结果';
 if(data&&Object.hasOwn(data,'found')){
  target.append(element('div',data.found?`${data.stops} 站 · ${data.transfers} 次换乘`:'当前网络不连通','route-summary'));
  for(let i=0;i<data.stations.length;i++){const s=data.stations[i],item=element('div',`${s.name_zh} · ${s.name_en}`,'route-stop');item.append(element('small',s.district));if(i<data.lines.length)item.append(element('span',data.lines[i],'tag'));target.append(item);}
  if(data.start_exits)target.append(element('pre',JSON.stringify({起点出口:data.start_exits,终点出口:data.end_exits},null,2)));
  target.append(element('p',data.message,'hint'));return;
 }
 if(data&&data.station){for(const [k,v]of Object.entries(data)){target.append(element('h3',({station:'站点信息',memberships:'所属线路',exits:'出口与地标'})[k]||k));showTable(v,target);}return;}
 if(data&&Object.hasOwn(data,'available')){target.append(element('div',data.available?`${data.amount} ${data.currency}`:data.message,'route-summary'));return;}
 target.append(element('pre',JSON.stringify(data,null,2)));
}
async function refresh(){
 const [stats,stations,lines,ds]=await Promise.all([api('stats'),api('stations'),api('lines'),api('districts')]);
 for(const key of ['stations','lines','exits','landmarks'])$('stat-'+key).textContent=Number(stats[0][key]).toLocaleString('en-US');
 allStations=stations;allLines=lines;districts=ds;
}
async function run(){
 const [action,label]=actionSpec(),button=operationButton();
 const view=current;
 const stillCurrent=()=>current===view&&actionSpec()?.[0]===action;
 if(action.endsWith('Delete')&&!confirm('确认执行删除？这会修改当前数据库。'))return;
 button.disabled=true;notice('正在处理…');
 try{
  const params=Object.fromEntries(new FormData($('operation-form')));
  for(const [key,value] of stationInputs)params[key]=value();
  const data=await api(action,params);
  if(action==='lineAdd')selectedLineId=String(data[0].line_id);
  if(stillCurrent()){
   render(data);
   if(action==='stations'&&data.length===0)notice('没有匹配站点。请检查搜索词，或切换匹配字段。');
   else notice(writes.has(action)?label+'完成':'');
  }
  try{
   if(action==='lineStations'||action==='lineInsert'||action==='lineRemove'){
    const rows=action==='lineStations'?data:await api('lineStations',{line_id:params.line_id});
    if(stillCurrent()){
     if(action!=='lineStations')render(rows);
     const line=allLines.find(l=>String(l.line_id)===params.line_id);
     $('result-title').textContent=`${line?line.name_zh+' · '+line.name_en:'线路 #'+params.line_id} · ${rows.length} 站`;
    }
   }
   if(writes.has(action)){
    await refresh();
    if(stillCurrent())fields();
   }
  }catch(e){if(stillCurrent())notice(label+'已完成，刷新失败：'+e.message,true);}
 }
 catch(e){
  if(stillCurrent()){
   $('result').replaceChildren(element('p','请检查输入后重试。','empty'));
   $('result-title').textContent=label+'失败';
   notice(e.message,true);
  }
 }finally{button.disabled=false;}
}
async function reloadResults(){
 try{
  await refresh();
  if(!writes.has(actionSpec()[0]))await run();
  else notice('站点、线路清单与统计已刷新；未重复执行修改操作。');
 }catch(e){notice(e.message,true);}
}
async function selectView(view){
 current=view;
 document.querySelectorAll('nav button').forEach(button=>{
  if(button.dataset.view===view)button.setAttribute('aria-current','page');
  else button.removeAttribute('aria-current');
 });
 $('title').textContent=groups[view].title;$('subtitle').textContent=groups[view].sub;$('operation').replaceChildren();
 for(const [value,label]of groups[view].actions)option($('operation'),value,label);fields();
 $('operation').disabled=false;
 $('reload').disabled=false;
 operationButton().disabled=false;
 if(view==='stations'||view==='lines'||view==='queries')await run();else{$('result').replaceChildren(element('p','选择起终点后开始查询。','empty'));notice('');}
}
$('operation-form').addEventListener('submit',e=>{e.preventDefault();run();});$('operation').addEventListener('change',fields);$('reload').addEventListener('click',reloadResults);
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>{
 if(current==='sql')window.location.href='/#'+b.dataset.view;
 else selectView(b.dataset.view);
}));

function startSqlPage() {
 current='sql';
 $('title').textContent='SQL 查询';
 $('subtitle').textContent='在项目数据库中执行只读 PostgreSQL 查询。';
 $('workspace').hidden=true;
 $('stats').hidden=true;
 $('sql-workspace').hidden=false;
 $('sql-nav').setAttribute('aria-current','page');
 document.querySelectorAll('nav button').forEach(button=>button.removeAttribute('aria-current'));
 const editor=$('sql-text');
 const example=editor.value;
 const form=$('sql-form');
 const submit=form.querySelector('button[type=submit]');
 $('sql-example').addEventListener('click',()=>{editor.value=example;editor.focus();});
 editor.addEventListener('keydown',event=>{
  if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){
   event.preventDefault();
   if(!submit.disabled)form.requestSubmit();
  }
 });
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(submit.disabled)return;
  const target=$('sql-result');
  target.replaceChildren();
  $('sql-result-title').textContent='查询结果';
  if(!editor.value.trim()){
   notice('请输入一条 SQL 查询。',true);
   editor.focus();
   return;
  }
  submit.disabled=true;
  notice('正在执行 SQL…');
  try {
   const data=await api('sqlQuery',{sql:editor.value});
   showTable(data.rows,target,data.columns);
   $('sql-result-title').textContent=`查询结果 · ${data.rows.length} 行`;
   const notes=[];
   if(data.truncated)notes.push('结果已截断。可加 WHERE 或 LIMIT 缩小范围。');
   if(data.clipped)notes.push('部分长字段只显示开头。');
   notice(notes.join(' ')||'SQL 执行完成。');
  } catch(e) {
   $('sql-result-title').textContent='SQL 执行失败';
   target.append(element('pre',e.message));
   notice('请根据下方错误修正语句后重试。',true);
  } finally {
   submit.disabled=false;
  }
 });
}

if(typeof window!=='undefined'&&window.location.pathname==='/sql')startSqlPage();
else {
 const requested=typeof window==='undefined'?'':window.location.hash.slice(1);
 refresh().then(()=>selectView(Object.hasOwn(groups,requested)?requested:'stations')).catch(e=>notice(e.message,true));
}
