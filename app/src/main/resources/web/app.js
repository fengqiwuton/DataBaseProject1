"use strict";
const $=id=>document.getElementById(id);
const token=document.querySelector('meta[name="metro-token"]').content;
const writes=new Set(['stationAdd','stationUpdate','stationDelete','lineAdd','lineUpdate','lineDelete','lineInsert','lineRemove','membershipUpdate']);
const groups={
 stations:{title:'站点与出口',sub:'从车站出发，查看城市轨道网络。',actions:[['stations','查询站点',['search']],['stationDetail','站点详情与出口',['station_id']],['stationAdd','新增站点',['name_zh','name_en','district_id','lon_mdeg','lat_mdeg']],['stationUpdate','修改站点',['station_id','name_zh','name_en','district_id','lon_mdeg','lat_mdeg']],['stationDelete','删除站点',['station_id']],['landmarks','查找地标',['search']]]},
 lines:{title:'线路编排',sub:'维护线路与站序，让每一站各归其位。',actions:[['lines','全部线路',[]],['lineStations','查看线路站序',['line_id']],['lineAdd','新增线路',['name_zh','name_en']],['lineUpdate','修改线路',['line_id','name_zh','name_en']],['lineDelete','删除线路',['line_id']],['lineInsert','指定位置插入站点',['line_id','position','station_ids','status','opening_year','first_train','last_train']],['lineRemove','移出线路',['line_id','station_id']],['membershipUpdate','更新线路站点属性',['line_id','station_id','status','opening_year','first_train','last_train']]]},
 routes:{title:'路线查询',sub:'选择出发与到达地点，探索线路连接。',actions:[['route','两站之间',['start','end','mode','planned']],['landmarkRoute','两地标之间',['start_landmark','end_landmark','mode','planned']],['fare','查询票价',['start','end']]]},
 queries:{title:'数据核验',sub:'使用项目规定的七类查询，核对数据准确性。',actions:[['q1','Q1 · 物理站点数量',[]],['q2','Q2 · 线路数量',[]],['q3','Q3 · 各区运营站数量',[]],['q4','Q4 · 线路开通年统计',['line_name']],['q5','Q5 · 出口最多站点',['line_name']],['q6','Q6 · 地标前缀',['prefix']],['q7','Q7 · 前后第 n 站',['station_name','line_name','n']]]}
};
const labels={search:'搜索词（可留空）',station_id:'站点',line_id:'线路',name_zh:'中文名称',name_en:'英文名称',district_id:'行政区',lon_mdeg:'经度 × 1000（可空）',lat_mdeg:'纬度 × 1000（可空）',position:'插入位置（从 1 开始）',station_ids:'站点 ID 列表（英文逗号分隔）',status:'运营状态',opening_year:'开通 / 预计开通年',first_train:'首班时间（可空）',last_train:'末班时间（可空）',start:'出发站',end:'到达站',mode:'路径偏好',planned:'网络范围',start_landmark:'起点地标完整名称',end_landmark:'终点地标完整名称',line_name:'线路英文名',station_name:'站点英文名',n:'前后站数 n',prefix:'LIKE 前缀（例如：塘朗%）',station_count:'站点数',line_count:'线路数',district:'行政区',cnt:'数量',opening:'开通年',english_name:'英文站名',chinese_name:'中文站名',exit:'出口',name:'地标名称',neighbor:'邻站',exit_code:'出口',landmark_name:'地标',exit_count:'出口数'};
let current='stations',allStations=[],allLines=[],districts=[];
function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
async function api(action,params={}){
 const body=new URLSearchParams({action,...params});
 const response=await fetch(writes.has(action)?'/api':'/api?'+body.toString(),writes.has(action)?{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','X-Metro-Token':token},body}:{});
 const result=await response.json();if(!response.ok)throw new Error(result.error||'请求失败');return result.data;
}
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
function option(select,value,label){const o=element('option',label);o.value=value;select.append(o);}
function actionSpec(){return groups[current].actions.find(a=>a[0]===$('operation').value);}
function fields(){
 const [action,,keys]=actionSpec();$('fields').replaceChildren();
 for(const key of keys){
  const label=element('label',labels[key]||key);let field;
  if(['station_id','start','end','line_id','district_id','status','mode','planned','line_name'].includes(key)){
   field=element('select');
   if(['station_id','start','end'].includes(key))for(const s of allStations)option(field,s.station_id,`${s.name_zh} · ${s.district} · #${s.station_id}`);
   if(key==='line_id')for(const l of allLines)option(field,l.line_id,`${l.name_zh} · ${l.name_en}`);
   if(key==='line_name')for(const l of allLines)option(field,l.name_en,l.name_en);
   if(key==='district_id')for(const d of districts)option(field,d.district_id,d.name_en);
   if(key==='status'){option(field,'Operation','运营 Operation');option(field,'Construction','在建 Construction');}
   if(key==='mode'){option(field,'stops','最少经过站数');option(field,'transfers','最少换乘，再最少站数');}
   if(key==='planned'){option(field,'false','仅运营网络');option(field,'true','包含在建网络');}
  }else{
   field=element('input');field.type=['position','opening_year','n','lon_mdeg','lat_mdeg'].includes(key)?'number':key.includes('train')?'time':'text';
   if(key==='position')field.value='1';if(key==='opening_year')field.value='2026';if(key==='n')field.value='2';
   if(key==='prefix')field.value='塘朗%';if(key==='station_name')field.value='Mawan';
  }
  field.name=key;field.required=!['search','lon_mdeg','lat_mdeg','first_train','last_train'].includes(key);label.append(field);$('fields').append(label);
 }
 $('hint').textContent=action==='lineInsert'?'可在站点查询结果中查看ID。批量插入使用同一运营状态、年份和时刻；插入失败时整批回滚。':action==='stationUpdate'?'选择站点后自动填充现有信息；清空坐标会删除坐标值。':action==='fare'?'源CSV未提供票价。只有配置经过认可的票价矩阵后，才显示相应价格。':action==='landmarkRoute'?'先在“站点与出口 → 查找地标”中查候选名称，复制完整地标名。':action==='q7'?'使用英文站名与完整线路英文名。返回先向较小站序、再向较大站序；越界显示空值。':'删除车站会同时删除出口并修复关联线路站序；移出线路保留车站。';
 if(action==='stationUpdate'){
  const fill=()=>{const s=allStations.find(s=>String(s.station_id)===$('operation-form').elements.station_id.value);if(s)for(const k of ['name_zh','name_en','district_id','lon_mdeg','lat_mdeg'])$('operation-form').elements[k].value=s[k]??'';};
  $('operation-form').elements.station_id.addEventListener('change',fill);fill();
 }
 if(action==='lineUpdate'){
  const fill=()=>{const l=allLines.find(l=>String(l.line_id)===$('operation-form').elements.line_id.value);if(l)for(const k of ['name_zh','name_en'])$('operation-form').elements[k].value=l[k];};
  $('operation-form').elements.line_id.addEventListener('change',fill);fill();
 }
}
function showTable(rows,parent){
 if(!rows.length){parent.append(element('p','没有匹配记录。','empty'));return;}
 const table=element('table'),head=element('thead'),hr=element('tr'),body=element('tbody');
 const keys=Object.keys(rows[0]);for(const k of keys)hr.append(element('th',labels[k]||k));head.append(hr);
 for(const r of rows){const row=element('tr');for(const k of keys)row.append(element('td',r[k]===null?'空值':String(r[k])));body.append(row);}
 table.append(head,body);parent.append(table);
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
 const [action,label]=actionSpec(),button=$('operation-form').querySelector('button');
 if(action.endsWith('Delete')&&!confirm('确认执行删除？这会修改当前数据库。'))return;
 button.disabled=true;notice('正在处理…');
 try{const data=await api(action,Object.fromEntries(new FormData($('operation-form'))));render(data);notice(label+'完成');if(writes.has(action)){await refresh();fields();}}
 catch(e){notice(e.message,true);}finally{button.disabled=false;}
}
async function reloadResults(){
 try{
  await refresh();
  if(!writes.has(actionSpec()[0]))await run();
  else notice('站点、线路清单与统计已刷新；未重复执行修改操作。');
 }catch(e){notice(e.message,true);}
}
async function selectView(view){
 current=view;document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
 $('title').textContent=groups[view].title;$('subtitle').textContent=groups[view].sub;$('operation').replaceChildren();
 for(const [value,label]of groups[view].actions)option($('operation'),value,label);fields();
 if(view==='stations'||view==='lines'||view==='queries')await run();else{$('result').replaceChildren(element('p','选择起终点后开始查询。','empty'));notice('');}
}
$('operation-form').addEventListener('submit',e=>{e.preventDefault();run();});$('operation').addEventListener('change',fields);$('reload').addEventListener('click',reloadResults);
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>selectView(b.dataset.view)));
refresh().then(()=>selectView('stations')).catch(e=>notice(e.message,true));
