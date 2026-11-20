import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const CLIENT_SOURCE = readFileSync(new URL('../pl-collapsible-card.js', import.meta.url), 'utf8');
const STORAGE_PREFIX = 'pl-collapsible-card:v1:';

class MemoryStorage {
  constructor(entries = {}) {
    this.entries = new Map(Object.entries(entries));
  }

  getItem(key) {
    return this.entries.get(key) ?? null;
  }

  setItem(key, value) {
    this.entries.set(key, value);
  }
}

function buildPage({ openStates, storage = new MemoryStorage(), variantId = '101' }) {
  const formListeners = new Map();
  const form = {
    dataset: {},
    addEventListener(type, listener) {
      formListeners.set(type, listener);
    },
    dispatch(type) {
      formListeners.get(type)?.();
    },
    querySelectorAll(selector) {
      assert.equal(selector, 'details.pl-collapsible-card');
      return cards;
    },
  };
  const container = { dataset: { variantId } };
  const cards = openStates.map((open) => {
    const listeners = new Map();
    return {
      dataset: {},
      open,
      addEventListener(type, listener) {
        listeners.set(type, listener);
      },
      closest(selector) {
        if (selector === 'form.question-form') return form;
        if (selector === '.question-container[data-variant-id]') return container;
        return null;
      },
      dispatch(type) {
        listeners.get(type)?.();
      },
    };
  });
  const context = vm.createContext({ window: { sessionStorage: storage } });
  vm.runInContext(CLIENT_SOURCE, context);

  return {
    cards,
    form,
    initialize() {
      cards.forEach((card) => context.window.PLCollapsibleCard(card));
    },
  };
}

test('restores and independently updates multiple card states', () => {
  const storage = new MemoryStorage({
    [`${STORAGE_PREFIX}101`]: JSON.stringify([false, true]),
  });
  const firstRender = buildPage({ openStates: [true, false], storage });

  firstRender.initialize();
  assert.deepEqual(
    firstRender.cards.map((card) => card.open),
    [false, true],
  );

  firstRender.cards[0].open = true;
  firstRender.cards[0].dispatch('toggle');
  assert.deepEqual(JSON.parse(storage.getItem(`${STORAGE_PREFIX}101`)), [true, true]);

  const secondRender = buildPage({ openStates: [false, false], storage });
  secondRender.initialize();
  assert.deepEqual(
    secondRender.cards.map((card) => card.open),
    [true, true],
  );
});

test('submission captures untouched state before score-driven rerendering', () => {
  const storage = new MemoryStorage();
  const firstRender = buildPage({ openStates: [true, false], storage });

  firstRender.initialize();
  firstRender.form.dispatch('submit');

  const gradedRender = buildPage({ openStates: [false, true], storage });
  gradedRender.initialize();
  assert.deepEqual(
    gradedRender.cards.map((card) => card.open),
    [true, false],
  );
});

test('state is isolated by variant and browser storage session', () => {
  const firstTabStorage = new MemoryStorage();
  const variantOne = buildPage({ openStates: [true], storage: firstTabStorage });
  variantOne.initialize();
  variantOne.form.dispatch('submit');

  const variantTwo = buildPage({
    openStates: [false],
    storage: firstTabStorage,
    variantId: '202',
  });
  variantTwo.initialize();
  assert.equal(variantTwo.cards[0].open, false);

  const secondTab = buildPage({ openStates: [false], storage: new MemoryStorage() });
  secondTab.initialize();
  assert.equal(secondTab.cards[0].open, false);
});

test('malformed or unavailable storage falls back to rendered state', () => {
  const malformedStorage = new MemoryStorage({ [`${STORAGE_PREFIX}101`]: 'not-json' });
  const malformedPage = buildPage({ openStates: [true], storage: malformedStorage });
  malformedPage.initialize();
  assert.equal(malformedPage.cards[0].open, true);

  const unavailableStorage = {
    getItem() {
      throw new Error('storage unavailable');
    },
    setItem() {
      throw new Error('storage unavailable');
    },
  };
  const unavailablePage = buildPage({ openStates: [false], storage: unavailableStorage });
  assert.doesNotThrow(() => {
    unavailablePage.initialize();
    unavailablePage.cards[0].open = true;
    unavailablePage.cards[0].dispatch('toggle');
    unavailablePage.form.dispatch('submit');
  });
  assert.equal(unavailablePage.cards[0].open, true);
});
