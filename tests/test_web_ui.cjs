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
