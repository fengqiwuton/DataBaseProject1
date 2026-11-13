const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

for (const mutation of ['stationDelete','lineDelete','lineRemove']) test('result refresh never replays '+mutation, async () => {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      handlers: {}, value: 'stationDelete', disabled: false, textContent: '',
      classList: { toggle() {} },
      addEventListener(name, handler) { this.handlers[name] = handler; },
      querySelector() { return get('submit'); }, replaceChildren() {}, append() {}
    });
    return elements.get(id);
  };
  const actions = [];
  const context = vm.createContext({
    document: { getElementById: get, querySelector: () => ({ content: 'test-token' }), querySelectorAll: () => [] },
    fetch: () => new Promise(() => {}), // Prevent automatic page initialization from racing the test.
    URLSearchParams, console, confirm: () => true,
    FormData: class { *[Symbol.iterator]() { yield ['station_id', '230']; } },
    record: action => actions.push(action)
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/src/main/resources/web/app.js'), 'utf8'), context);
  vm.runInContext(`
    api = async function(action) { record(action); return []; };
    refresh = async function() { record('inventoryRead'); };
    fields = function() {};
    render = function() {};
    actionSpec = function() { return [${JSON.stringify(mutation)}, '修改操作', []]; };
  `, context);
  await get('reload').handlers.click();
  await get('reload').handlers.click();
  assert.ok(actions.every(a => a === 'inventoryRead'),
    'refresh must not issue any mutation: ' + actions.join(','));
  assert.ok(actions.length > 0, 'refresh must refresh inventory or read results');
});

test('line edits show the new Num order for the submitted line', async () => {
  const get = (() => {
    const map = new Map();
    return id => {
      if (!map.has(id)) map.set(id, {
        children: [], value: '', textContent: '', classList: { toggle() {} },
        addEventListener() {}, querySelector() { return get('submit'); },
        replaceChildren(...children) { this.children = children; }, append(child) { this.children.push(child); }
      });
      return map.get(id);
    };
  })();
  const actions = [];
  const context = vm.createContext({
    document: {
      getElementById: get, querySelector: () => ({ content: 'test-token' }), querySelectorAll: () => [],
      createElement: tag => ({
        tag, value: '', children: [], handlers: {}, setAttribute() {}, focus() {},
        addEventListener(name, handler) { this.handlers[name] = handler; },
        replaceChildren(...children) { this.children = children; },
        append(...children) { this.children.push(...children); }
      })
    },
    fetch: () => new Promise(() => {}),
    URLSearchParams,
    FormData: class {
      *[Symbol.iterator]() {
        for (const label of get('fields').children) {
          const [input] = label.children;
          if (input?.name) yield [input.name, input.value ?? ''];
        }
      }
    },
    record: (action, line) => actions.push([action, line])
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/src/main/resources/web/app.js'), 'utf8'), context);
  await vm.runInContext(`
    current = 'lines';
    allLines = [{line_id: 1, name_zh: '一号线', name_en: 'Line 1'}, {line_id: 29, name_zh: '答辩线', name_en: 'Demo Line'}];
    allStations = [
      {station_id: 200, name_zh: '罗湖', name_en: 'Luohu', district: 'Luohu'},
      {station_id: 439, name_zh: '梨园', name_en: 'Liyuan', district: 'Luohu'},
      {station_id: 438, name_zh: '梨园', name_en: 'Liyuan', district: 'Longgang'}
    ];
    refresh = async function() {};
    api = async function(action, params) {
      record(action, params.line_id);
      if (action === 'lineInsert') record('insert order', params.station_ids);
      if (action === 'lineRemove') record('remove station', params.station_id);
      if (action === 'lineAdd') return [{line_id: 29}];
      if (action === 'lineStations') return [{station_id: 200, position: 1}, {station_id: 439, position: 2}];
      return {message: 'OK'};
    };
    (async () => {
      $('operation').value = 'lineAdd';
      fields();
      await run();
      for (const action of ['lineInsert', 'lineRemove']) {
        $('operation').value = action;
        fields();
        record('selected', $('fields').children[0].children[0].value);
        const picker=$('fields').children[action==='lineInsert'?2:1];
        const input=picker.children[1].children[0];
        const candidates=picker.children[2].children[0];
        if (action==='lineInsert') {
          input.value='Liyuan';
          input.handlers.input();
          await run();
          record('ambiguous', $('notice').textContent.includes('2 个站点'));
          candidates.value='439';
          picker.children[4].handlers.click();
          input.value='Luohu';
          input.handlers.input();
        } else {
          input.value='#439';
          input.handlers.input();
        }
        await run();
      }
    })();
  `, context);
  assert.deepEqual(actions, [
    ['lineAdd', undefined], ['selected', '29'], ['ambiguous', true],
    ['lineInsert', '29'], ['insert order', '439,200'], ['lineStations', '29'],
    ['selected', '29'], ['lineRemove', '29'], ['remove station', '439'], ['lineStations', '29']
  ]);
  const [head, body] = get('result').children[0].children;
  assert.deepEqual(head.children[0].children.map(cell => cell.textContent), ['站点编号', 'Num（站序）']);
  assert.deepEqual(body.children.map(row => row.children.map(cell => cell.textContent)), [['200', '1'], ['439', '2']]);
});
