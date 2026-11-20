(() => {
  'use strict';

  const CARD_SELECTOR = 'details.pl-collapsible-card';
  const STORAGE_PREFIX = 'pl-collapsible-card:v1:';

  function readStates(storageKey) {
    try {
      const storedValue = window.sessionStorage.getItem(storageKey);
      if (storedValue === null) return [];

      const states = JSON.parse(storedValue);
      return Array.isArray(states) ? states : [];
    } catch {
      return [];
    }
  }

  function writeStates(storageKey, states) {
    try {
      window.sessionStorage.setItem(storageKey, JSON.stringify(states));
    } catch {
      // Storage may be unavailable because of browser privacy settings or quota limits.
    }
  }

  function saveFormState(form, storageKey) {
    const states = Array.from(form.querySelectorAll(CARD_SELECTOR), (card) => card.open);
    writeStates(storageKey, states);
  }

  function saveCardState(card, storageKey, index) {
    const states = readStates(storageKey);
    states[index] = card.open;
    writeStates(storageKey, states);
  }

  window.PLCollapsibleCard = (card) => {
    const form = card.closest('form.question-form');
    const container = card.closest('.question-container[data-variant-id]');
    const variantId = container?.dataset.variantId;
    if (form === null || !variantId) return;

    const cards = Array.from(form.querySelectorAll(CARD_SELECTOR));
    const index = cards.indexOf(card);
    if (index < 0) return;

    const storageKey = `${STORAGE_PREFIX}${variantId}`;
    const storedState = readStates(storageKey)[index];
    if (typeof storedState === 'boolean') card.open = storedState;

    if (card.dataset.plCollapsibleCardInitialized !== 'true') {
      card.dataset.plCollapsibleCardInitialized = 'true';
      card.addEventListener('toggle', () => saveCardState(card, storageKey, index));
    }

    if (form.dataset.plCollapsibleCardInitialized !== 'true') {
      form.dataset.plCollapsibleCardInitialized = 'true';
      form.addEventListener('submit', () => saveFormState(form, storageKey));
    }
  };
})();
