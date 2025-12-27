<script lang="ts">
  import { onMount, tick } from "svelte";
  import { fade, slide, fly, scale } from "svelte/transition";
  import { Plug, PlugZap, Settings } from "lucide-svelte";

  interface Flashcard {
    front: string;
    back: string;
    refining: boolean;
    refineInput: string;
  }

  let inputText = "";
  let cards: Flashcard[] = [];
  let loading = false;
  let status = "";
  let error = "";
  let apiReady = false;

  const textModels = [
    { id: "gemini-3-pro-preview", name: "Gemini 3 Pro Preview" },
    { id: "gemini-3-flash-preview", name: "Gemini 3 Flash Preview" },
    { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro" },
    { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash" },
    { id: "gemini-2.5-flash-lite", name: "Gemini 2.5 Flash-Lite" },
    { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash" },
    { id: "gemini-2.0-flash-lite", name: "Gemini 2.0 Flash-Lite" },
    { id: "gemini-1.5-flash", name: "Gemini 1.5 Flash (Legacy)" },
  ];

  let selectedModel = "gemini-1.5-flash"; // Default backup
  // Try to find gemini-3-flash
  const defaultModelObj =
    textModels.find((m) => m.id.includes("3-flash")) ||
    textModels.find((m) => m.id.includes("1.5-flash"));
  if (defaultModelObj) {
    selectedModel = defaultModelObj.id;
  }

  let decks = ["Default"];
  let selectedDeck = "Default";
  let showNewDeckInput = false;
  let newDeckName = "";
  let cardsListElement: HTMLElement;
  let ankiOnline = false;
  let expandedIndex = -1;
  let showSettings = false;
  let geminiApiKey = "";
  let aiSystemPrompt = "";

  function toggleExpand(index: number) {
    expandedIndex = expandedIndex === index ? -1 : index;
  }

  async function fetchDecks() {
    try {
      // @ts-ignore
      if (typeof pywebview === "undefined") return;
      // @ts-ignore
      const result = await pywebview.api.get_decks();
      if (result.status === "success") {
        ankiOnline = true;
        decks = result.decks;
        if (!decks.includes(selectedDeck) && decks.length > 0) {
          selectedDeck = decks.includes("Default") ? "Default" : decks[0];
        }
      } else {
        ankiOnline = false;
      }
    } catch (e) {
      ankiOnline = false;
      console.error("Failed to fetch decks", e);
    }
  }

  async function fetchSettings() {
    try {
      // @ts-ignore
      if (typeof pywebview === "undefined") return;
      // @ts-ignore
      const settings = await pywebview.api.get_settings();
      geminiApiKey = settings.gemini_api_key;
      aiSystemPrompt = settings.ai_system_prompt;
    } catch (e) {
      console.error("Failed to fetch settings", e);
    }
  }

  async function saveSettings() {
    loading = true;
    try {
      // @ts-ignore
      const result = await pywebview.api.save_settings(
        geminiApiKey,
        aiSystemPrompt,
      );
      if (result.status === "success") {
        showStatus("Settings saved successfully!", 3000);
        showSettings = false;
      } else {
        error = result.message;
      }
    } catch (e) {
      error = "Failed to save settings.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    const handleReady = () => {
      apiReady = true;
      fetchDecks();
      fetchSettings();
      // Periodically check Anki status
      setInterval(fetchDecks, 5000);
    };

    // @ts-ignore
    if (typeof pywebview !== "undefined") {
      handleReady();
    } else {
      window.addEventListener("pywebviewready", handleReady);
    }

    // @ts-ignore
    window.receiveCard = (card: any) => {
      const newCard: Flashcard = {
        ...card,
        refining: false,
        refineInput: "",
      };
      cards = [...cards, newCard];
      // Scroll to bottom of list
      if (cardsListElement) {
        tick().then(() => {
          cardsListElement.scrollTop = cardsListElement.scrollHeight;
        });
      }
    };

    return () => {
      window.removeEventListener("pywebviewready", handleReady);
      // @ts-ignore
      delete window.receiveCard;
    };
  });

  function showStatus(msg: string, duration = 3000) {
    status = msg;
    if (duration > 0) {
      setTimeout(() => {
        if (status === msg) status = "";
      }, duration);
    }
  }

  async function createDeck() {
    if (!newDeckName.trim()) return;
    loading = true;
    try {
      // @ts-ignore
      const result = await pywebview.api.create_deck(newDeckName.trim());
      if (result.status === "success") {
        selectedDeck = newDeckName.trim();
        await fetchDecks();
        showNewDeckInput = false;
        newDeckName = "";
        showStatus("Deck created successfully!", 3000);
      } else {
        error = result.message;
      }
    } catch (e) {
      error = "Failed to create deck.";
    } finally {
      loading = false;
    }
  }

  async function generateCards() {
    if (!inputText.trim()) return;
    loading = true;
    error = "";
    status = "Anki AI is extracting...";

    try {
      // @ts-ignore
      const result = await pywebview.api.generate_cards_stream(
        inputText,
        selectedModel,
        aiSystemPrompt,
      );
      if (result.status === "success") {
        showStatus(`Generation complete.`, 3000);
        inputText = ""; // Clear input for next paste
      } else {
        error = result.message;
      }
    } catch (e) {
      error = "Communication error.";
    } finally {
      loading = false;
    }
  }

  async function refineCard(index: number) {
    const card = cards[index];
    if (!card.refineInput.trim()) return;

    card.refining = true;
    cards = [...cards];

    try {
      // @ts-ignore
      const result = await pywebview.api.refine_card(
        card.front,
        card.back,
        card.refineInput,
        selectedModel,
      );
      if (result.status === "success") {
        cards[index] = {
          ...result.card,
          refining: false,
          refineInput: "",
        };
        cards = [...cards];
        showStatus("Card refined by AI.", 2000);
      } else {
        error = result.message;
        card.refining = false;
        cards = [...cards];
      }
    } catch (e) {
      error = "Refinement failed.";
      card.refining = false;
      cards = [...cards];
    }
  }

  async function insertToAnki() {
    if (cards.length === 0) return;
    loading = true;
    error = "";
    status = "Injecting staged cards...";

    try {
      // @ts-ignore
      const result = await pywebview.api.insert_cards(cards, selectedDeck);
      if (result.status === "success") {
        let msg = `Injected ${result.count} cards!`;
        if (result.duplicates > 0) {
          msg += ` ${result.duplicates} skipped as duplicates.`;
        }
        if (result.errors && result.errors.length > 0) {
          msg += ` ${result.errors.length} failed.`;
          error = result.errors[0]; // Show first error in status bar
        }
        showStatus(msg, 5000);

        // Clear list if we did work (successes or duplicates)
        if (result.count > 0 || result.duplicates > 0) {
          cards = [];
        }
      } else {
        error = result.message;
      }
    } catch (e) {
      error = "Anki connection failed.";
    } finally {
      loading = false;
    }
  }

  function removeCard(index: number) {
    cards = cards.filter((_, i) => i !== index);
  }

  function format(command: string, value: string | undefined = undefined) {
    document.execCommand(command, false, value);
  }
</script>

<div
  class="h-screen flex flex-col bg-[#f5f5f5] text-[#333] font-sans overflow-hidden"
>
  <!-- Top Header -->
  <header
    class="h-12 bg-white border-b border-[#ddd] flex shrink-0 items-center justify-between px-6 z-50"
  >
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-3">
        <!-- <img src="/logo.png" alt="Logo" class="w-24 h-24 shadow-sm" /> -->
        <span class="text-base font-bold tracking-tight"
          >Anki<span class="text-[#2563eb]">Inject</span></span
        >
      </div>
    </div>

    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2">
        <span class="text-[10px] uppercase font-bold text-slate-400">Model</span
        >
        <select
          bind:value={selectedModel}
          class="bg-[#fcfcfc] border border-[#ddd] text-[11px] px-2 py-0.5 rounded text-slate-600 outline-none focus:border-[#00aaff] cursor-pointer"
        >
          {#each textModels as model}
            <option value={model.id}>{model.name}</option>
          {/each}
        </select>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-[10px] uppercase font-bold text-slate-400"
          >Target Deck</span
        >
        {#if showNewDeckInput}
          <div
            class="flex gap-1 items-center bg-white border border-[#ddd] p-0.5 rounded shadow-sm"
          >
            <input
              bind:value={newDeckName}
              placeholder="Deck name..."
              class="bg-transparent text-[11px] px-2 w-24 outline-none"
            />
            <button
              on:click={createDeck}
              class="text-[#00aaff] text-[11px] font-bold px-1 hover:text-[#0099ee]"
              >OK</button
            >
            <button
              on:click={() => (showNewDeckInput = false)}
              class="text-slate-300 text-[11px] px-1 hover:text-red-500"
              >✕</button
            >
          </div>
        {:else}
          <div class="flex items-center gap-2">
            <select
              bind:value={selectedDeck}
              class="bg-[#fcfcfc] border border-[#ddd] text-[11px] px-2 py-0.5 rounded text-slate-600 outline-none focus:border-[#00aaff] min-w-[100px] cursor-pointer"
            >
              {#each decks as deck}
                <option value={deck}>{deck}</option>
              {/each}
            </select>
            <button
              on:click={() => (showNewDeckInput = true)}
              class="bg-[#f5f5f5] hover:bg-[#eee] border border-[#ddd] text-[#00aaff] px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tight transition-colors shadow-sm active:scale-95"
            >
              + New
            </button>
          </div>
        {/if}
      </div>
      <!-- Anki Status Indicator (Connector Icon) -->
      <div
        class="relative flex items-center justify-center w-8 h-8 rounded-full transition-colors duration-300 {ankiOnline
          ? 'text-emerald-500 bg-emerald-50'
          : 'text-slate-300 bg-slate-50'}"
        title={ankiOnline ? "Anki Connected" : "Anki Disconnected"}
      >
        {#if ankiOnline}
          <PlugZap size="18" strokeWidth="2" />
        {:else}
          <Plug size="18" strokeWidth="2" />
        {/if}

        <!-- Pulse Dot for Online -->
        {#if ankiOnline}
          <span
            class="absolute top-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-white animate-pulse"
          ></span>
        {/if}
      </div>

      <!-- Settings Button -->
      <button
        on:click={() => (showSettings = true)}
        class="p-2 text-slate-400 hover:text-[#00aaff] transition-colors rounded-full hover:bg-slate-100"
        aria-label="Settings"
        title="Settings"
      >
        <Settings size="20" strokeWidth="2.5" />
      </button>
    </div>
  </header>

  <!-- Side-by-Side Content -->
  <div class="flex-1 flex overflow-hidden">
    <!-- Left Panel: Input -->
    <div class="w-1/2 flex flex-col border-r border-[#ddd] bg-white">
      <div
        class="px-4 py-2 bg-[#fcfcfc] border-b border-[#eee] flex items-center justify-between shadow-sm shrink-0"
      >
        <h3
          class="text-[11px] font-bold uppercase tracking-wider text-slate-400"
        >
          Paste Study Notes
        </h3>
        <button
          on:click={async () => {
            try {
              // @ts-ignore
              const result = await pywebview.api.read_clipboard();
              if (result.status === "success") {
                inputText = result.text;
              } else {
                console.error("Clipboard error:", result.message);
              }
            } catch (err) {
              console.error("Bridge clipboard failed", err);
            }
          }}
          class="bg-slate-900 hover:bg-black text-white px-5 py-1 rounded-full font-bold text-xs shadow-sm transition-all flex items-center gap-1.5 active:scale-95"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-3 h-3"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="3"
            ><path
              d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"
            /><rect x="8" y="2" width="8" height="4" rx="1" ry="1" /></svg
          >
          Paste
        </button>
      </div>
      <textarea
        bind:value={inputText}
        placeholder="Paste your source text here. Generated cards will be added to the Stage on the right."
        class="flex-1 w-full bg-transparent p-6 text-sm text-slate-700 placeholder-slate-300 focus:outline-none resize-none leading-relaxed"
      ></textarea>

      <div
        class="p-4 border-t border-[#eee] bg-[#fcfcfc] flex items-center justify-between"
      >
        <div
          class="text-[11px] font-medium text-slate-300 uppercase tracking-widest"
        >
          {inputText.split(/\s+/).filter(Boolean).length} words ready
        </div>
        <button
          on:click={generateCards}
          disabled={loading || !inputText.trim()}
          class="bg-[#00aaff] hover:bg-[#0099ee] text-white px-8 py-2 rounded-full font-bold text-sm shadow-sm disabled:opacity-50 transition-all active:scale-95 flex items-center gap-2"
        >
          {#if loading}
            <div
              class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
            ></div>
          {/if}
          Generate & Stage
        </button>
      </div>
    </div>

    <!-- Right Panel: Staged List -->
    <div class="w-1/2 flex flex-col bg-[#f5f5f5]">
      <div
        class="px-4 py-2 bg-[#fcfcfc] border-b border-[#ddd] flex items-center justify-between shadow-sm shrink-0"
      >
        <h3
          class="text-[11px] font-bold uppercase tracking-wider text-slate-400"
        >
          Staged Card List ({cards.length})
        </h3>
        <button
          on:click={insertToAnki}
          disabled={loading || cards.length === 0}
          class="bg-emerald-500 hover:bg-emerald-600 text-white px-5 py-1 rounded-full font-bold text-xs shadow-sm disabled:opacity-30 transition-all flex items-center gap-1.5"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-3 h-3"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="3"><path d="M5 12h14M12 5l7 7-7 7" /></svg
          >
          Inject All to Anki
        </button>
      </div>

      <div
        bind:this={cardsListElement}
        class="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {#if cards.length === 0}
          <div
            class="h-full flex flex-col items-center justify-center text-slate-300 gap-2 opacity-50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-12 h-12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1"
              ><rect x="3" y="4" width="18" height="16" rx="2" /><path
                d="M7 8h10M7 12h10M7 16h10"
              /></svg
            >
            <p class="text-xs font-medium uppercase tracking-widest">
              No cards staged
            </p>
          </div>
        {/if}

        {#each cards as card, i (i)}
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div
            transition:slide|local={{ duration: 200 }}
            class="bg-white border border-[#ddd] hover:border-[#aaa] rounded-lg shadow-sm hover:shadow transition-all group cursor-pointer relative"
            on:click={() => toggleExpand(i)}
            on:keydown={(e) =>
              (e.key === "Enter" || e.key === " ") && toggleExpand(i)}
            role="button"
            tabindex="0"
          >
            <!-- side-by-side compact view -->
            <div class="flex items-stretch divide-x divide-[#eee]">
              <div class="flex-1 p-3 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span
                    class="text-[8px] font-black text-slate-300 uppercase tracking-widest"
                    >Front</span
                  >
                  <span
                    class="text-[8px] font-black text-slate-100 uppercase tracking-widest"
                    >#{i + 1}</span
                  >
                </div>
                <div
                  class="text-[11px] text-slate-600 line-clamp-3 prose prose-sm max-w-none prose-slate"
                >
                  {@html card.front}
                </div>
              </div>
              <div class="flex-1 p-3 min-w-0 bg-[#fdfdfd]">
                <div class="flex items-center gap-2 mb-1">
                  <span
                    class="text-[8px] font-black text-slate-300 uppercase tracking-widest"
                    >Back</span
                  >
                </div>
                <div
                  class="text-[11px] text-slate-500 line-clamp-3 prose prose-sm max-w-none prose-slate"
                >
                  {@html card.back}
                </div>
              </div>
            </div>

            <!-- Action Buttons (Top Right) -->
            <div
              class="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10"
            >
              <button
                on:click|stopPropagation={() => toggleExpand(i)}
                class="bg-white border border-[#ddd] hover:border-[#00aaff] text-slate-400 hover:text-[#00aaff] p-1.5 rounded-lg shadow-sm transition-all active:scale-90"
                aria-label="Edit card"
                title="Edit Card"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  ><path
                    d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                  /><path
                    d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                  /></svg
                >
              </button>
              <button
                on:click|stopPropagation={() => removeCard(i)}
                class="bg-white border border-[#ddd] hover:border-red-500 text-slate-400 hover:text-red-500 p-1.5 rounded-lg shadow-sm transition-all active:scale-90"
                aria-label="Remove card"
                title="Remove Card"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12" /></svg
                >
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Centered Modal Editor -->
  {#if expandedIndex !== -1}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      transition:fade={{ duration: 150 }}
      class="fixed inset-0 z-[200] flex items-center justify-center p-8 bg-slate-900/50 backdrop-blur-sm"
      on:click={() => (expandedIndex = -1)}
    >
      <div
        transition:scale={{ duration: 300, start: 0.95 }}
        class="bg-white w-full max-w-4xl shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[90vh] border border-white/20"
        on:click|stopPropagation
      >
        <!-- Modal Header -->
        <div
          class="px-6 py-4 border-b border-[#eee] bg-[#fcfcfc] flex items-center justify-between"
        >
          <div class="flex items-center gap-3">
            <span
              class="bg-[#00aaff] text-white text-[10px] font-black px-2 py-0.5 rounded uppercase font-mono tracking-tighter shadow-sm"
              >Card Editor</span
            >
            <span
              class="text-slate-400 text-xs font-bold uppercase tracking-widest opacity-40"
              >#{expandedIndex + 1}</span
            >
          </div>
          <button
            on:click={() => (expandedIndex = -1)}
            class="bg-slate-50 hover:bg-[#00aaff] text-slate-400 hover:text-white px-6 py-2 rounded-full text-[11px] font-black uppercase tracking-tight shadow-sm transition-all flex items-center gap-2 group"
          >
            Done Editing
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="3.5"><polyline points="20 6 9 17 4 12" /></svg
            >
          </button>
        </div>

        <!-- Enhanced Toolbar -->
        <div
          class="px-6 py-2 bg-[#f8f8f8] border-b border-[#eee] flex items-center gap-1.5 shrink-0"
        >
          <div class="flex items-center gap-1 border-r border-[#ddd] pr-3 mr-2">
            <button
              on:mousedown|preventDefault={() => format("bold")}
              class="w-8 h-8 flex items-center justify-center hover:bg-white hover:border-[#ddd] border border-transparent rounded-lg text-xs font-black text-slate-700 transition-all shadow-sm active:scale-90"
              title="Bold">B</button
            >
            <button
              on:mousedown|preventDefault={() => format("italic")}
              class="w-8 h-8 flex items-center justify-center hover:bg-white hover:border-[#ddd] border border-transparent rounded-lg text-xs font-bold italic text-slate-700 transition-all shadow-sm active:scale-90"
              title="Italic">I</button
            >
            <button
              on:mousedown|preventDefault={() => format("underline")}
              class="w-8 h-8 flex items-center justify-center hover:bg-white hover:border-[#ddd] border border-transparent rounded-lg text-xs font-bold underline text-slate-700 transition-all shadow-sm active:scale-90"
              title="Underline">U</button
            >
          </div>
          <div class="flex items-center gap-1 border-r border-[#ddd] pr-3 mr-2">
            <button
              on:mousedown|preventDefault={() => format("insertUnorderedList")}
              class="w-8 h-8 flex items-center justify-center hover:bg-white hover:border-[#ddd] border border-transparent rounded-lg transition-all shadow-sm active:scale-90"
              title="Bullet List"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-4 h-4 text-slate-700"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                ><line x1="8" y1="6" x2="21" y2="6" /><line
                  x1="8"
                  y1="12"
                  x2="21"
                  y2="12"
                /><line x1="8" y1="18" x2="21" y2="18" /><line
                  x1="3"
                  y1="6"
                  x2="3.01"
                  y2="6"
                /><line x1="3" y1="12" x2="3.01" y2="12" /><line
                  x1="3"
                  y1="18"
                  x2="3.01"
                  y2="18"
                /></svg
              >
            </button>
            <button
              on:mousedown|preventDefault={() => format("insertOrderedList")}
              class="w-8 h-8 flex items-center justify-center hover:bg-white hover:border-[#ddd] border border-transparent rounded-lg transition-all shadow-sm active:scale-90"
              title="Numbered List"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-4 h-4 text-slate-700"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                ><line x1="10" y1="6" x2="21" y2="6" /><line
                  x1="10"
                  y1="12"
                  x2="21"
                  y2="12"
                /><line x1="10" y1="18" x2="21" y2="18" /><path
                  d="M4 6h1v4"
                /><path d="M4 10h2" /></svg
              >
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-10 space-y-10 bg-white">
          <div class="grid grid-cols-2 gap-12">
            <div class="space-y-4 flex flex-col">
              <div class="flex items-center justify-between">
                <span
                  class="text-[10px] font-black text-[#00aaff] uppercase tracking-[3px]"
                  >Questions / Front</span
                >
              </div>
              <div
                contenteditable="true"
                bind:innerHTML={cards[expandedIndex].front}
                class="w-full min-h-[300px] text-lg text-slate-700 focus:outline-none prose max-w-none leading-relaxed prose-slate focus:pl-1 transition-all"
              ></div>
            </div>

            <div
              class="space-y-4 flex flex-col border-l border-[#f5f5f5] pl-12"
            >
              <div class="flex items-center justify-between">
                <span
                  class="text-[10px] font-black text-[#00aaff] uppercase tracking-[3px]"
                  >Answers / Back</span
                >
              </div>
              <div
                contenteditable="true"
                bind:innerHTML={cards[expandedIndex].back}
                class="w-full min-h-[300px] text-lg text-slate-500 focus:outline-none prose max-w-none leading-relaxed prose-slate focus:pl-1 transition-all"
              ></div>
            </div>
          </div>
        </div>

        <!-- AI Refine Workspace -->
        <div class="p-10 bg-[#fcfcfc] border-t border-[#eee]">
          <div class="space-y-4 flex flex-col max-w-4xl mx-auto">
            <!-- Label Header -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-1 h-3 bg-slate-400 rounded-full"></div>
                <span
                  class="text-[10px] font-black text-slate-500 uppercase tracking-[3px]"
                  >AI Instructions</span
                >
              </div>
              <span
                class="text-[8px] font-bold text-slate-300 uppercase tracking-widest"
                >Powered by Gemini</span
              >
            </div>

            <!-- Standard Input Area -->
            <div class="relative group">
              <textarea
                bind:value={cards[expandedIndex].refineInput}
                placeholder="e.g. 'Simplify the phrasing', 'Fix grammar', 'Add context about...'"
                class="w-full min-h-[100px] p-4 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-[#00aaff] focus:ring-4 focus:ring-[#00aaff]/5 transition-all resize-none shadow-sm"
                on:keydown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    refineCard(expandedIndex);
                  }
                }}
              ></textarea>

              <!-- Action Bar (Bottom Right of Input) -->
              <div class="absolute bottom-3 right-3 flex items-center gap-2">
                <button
                  on:click={() => refineCard(expandedIndex)}
                  disabled={cards[expandedIndex].refining ||
                    !cards[expandedIndex].refineInput.trim()}
                  class="bg-slate-800 hover:bg-black text-white px-4 py-1.5 rounded-md text-[10px] font-black uppercase tracking-wide shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95 flex items-center gap-2"
                >
                  {#if cards[expandedIndex].refining}
                    <div
                      class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"
                    ></div>
                    <span>Working...</span>
                  {:else}
                    <span>Apply Refinement</span>
                  {/if}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Status Bar / Toasts -->
  {#if status || error}
    <div
      transition:fly={{ y: 20 }}
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] min-w-[340px] pointer-events-none"
    >
      <div
        class="bg-white border border-[#ddd] shadow-xl rounded-lg overflow-hidden flex items-center p-4 gap-4 pointer-events-auto"
      >
        <div class="shrink-0">
          {#if error}
            <div
              class="w-8 h-8 rounded-full bg-red-50 flex items-center justify-center text-red-500 scale-90 border border-red-100"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"><path d="M18 6 6 18M6 6l12 12" /></svg
              >
            </div>
          {:else}
            <div
              class="w-8 h-8 rounded-full bg-[#f0f9ff] flex items-center justify-center text-[#00aaff] scale-90 border border-blue-50"
            >
              {#if loading}
                <div
                  class="w-4 h-4 border-2 border-[#00aaff]/30 border-t-[#00aaff] rounded-full animate-spin"
                ></div>
              {:else}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3.5"><polyline points="20 6 9 17 4 12" /></svg
                >
              {/if}
            </div>
          {/if}
        </div>

        <div class="flex-1 min-w-0">
          <p
            class="text-[9px] uppercase font-black tracking-widest text-slate-400 leading-none mb-1.5"
          >
            {error ? "Attention" : "System Status"}
          </p>
          <p class="text-[12px] font-bold text-slate-700 leading-tight pr-4">
            {error || status}
          </p>
        </div>

        <button
          on:click={() => {
            status = "";
            error = "";
          }}
          aria-label="Close notification"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12" /></svg
          >
        </button>
      </div>
    </div>
  {/if}
  <!-- Settings Modal -->
  {#if showSettings}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      transition:fade={{ duration: 150 }}
      class="fixed inset-0 z-[300] flex items-center justify-center p-8 bg-slate-900/50 backdrop-blur-sm"
      on:click={() => (showSettings = false)}
    >
      <div
        transition:scale={{ duration: 300, start: 0.95 }}
        class="bg-white w-full max-w-md shadow-2xl rounded-2xl overflow-hidden flex flex-col border border-white/20"
        on:click|stopPropagation
      >
        <div
          class="px-6 py-4 border-b border-[#eee] bg-[#fcfcfc] flex items-center justify-between"
        >
          <h2
            class="text-sm font-black uppercase tracking-widest text-slate-700"
          >
            Settings
          </h2>
          <button
            on:click={() => (showSettings = false)}
            class="text-slate-300 hover:text-slate-500 transition-colors"
            aria-label="Close settings"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-5 h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12" /></svg
            >
          </button>
        </div>

        <div class="p-6 space-y-6">
          <div class="space-y-2">
            <label
              class="text-[10px] font-black uppercase tracking-[2px] text-[#00aaff] block"
              for="api-key"
            >
              Gemini API Key
            </label>
            <div class="relative flex items-center">
              <input
                id="api-key"
                type="password"
                bind:value={geminiApiKey}
                placeholder="Enter your API Key..."
                class="w-full bg-[#f8f8f8] border border-[#ddd] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#00aaff]/40 focus:ring-4 focus:ring-[#00aaff]/5 transition-all"
              />
            </div>
            <p class="text-[10px] text-slate-400 leading-relaxed">
              Your key is saved locally in your OS config folder.
            </p>
          </div>

          <div class="space-y-2">
            <label
              class="text-[10px] font-black uppercase tracking-[2px] text-[#00aaff] block"
              for="ai-prompt"
            >
              Default AI System Prompt
            </label>
            <div class="relative">
              <textarea
                id="ai-prompt"
                bind:value={aiSystemPrompt}
                placeholder="Custom instruction for card generation..."
                class="w-full bg-[#f8f8f8] border border-[#ddd] rounded-xl px-4 py-3 text-xs min-h-[100px] resize-none focus:outline-none focus:border-[#00aaff]/40 focus:ring-4 focus:ring-[#00aaff]/5 transition-all scrollbar-thin"
              ></textarea>
            </div>
            <p class="text-[10px] text-slate-400 leading-relaxed">
              Define how the AI should format cards or what content to
              prioritize.
            </p>
          </div>
        </div>

        <div
          class="px-6 py-4 bg-[#fcfcfc] border-t border-[#eee] flex items-center justify-end gap-3"
        >
          <button
            on:click={() => (showSettings = false)}
            class="px-5 py-2 rounded-full text-[11px] font-bold text-slate-400 hover:text-slate-600 uppercase tracking-tight transition-all"
          >
            Cancel
          </button>
          <button
            on:click={saveSettings}
            disabled={loading}
            class="bg-slate-900 hover:bg-black text-white px-8 py-2 rounded-full text-[11px] font-black uppercase tracking-widest shadow-lg disabled:opacity-20 transition-all active:scale-95"
          >
            {loading ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  :global(.prose b) {
    font-weight: 700;
    color: #111;
  }
  :global(.prose i) {
    font-style: italic;
  }
  :global(.prose ul) {
    list-style-type: disc;
    padding-left: 1.25rem;
    margin: 0.5rem 0;
  }
  :global(.prose li) {
    margin: 0.25rem 0;
  }

  :global(body) {
    background: #f5f5f5;
    margin: 0;
    overflow: hidden;
  }

  textarea {
    font-family: inherit;
    scrollbar-width: thin;
    scrollbar-color: #ddd transparent;
  }

  [contenteditable="true"]:empty:before {
    content: attr(placeholder);
    color: #ccc;
  }

  div::-webkit-scrollbar {
    width: 6px;
  }

  textarea::-webkit-scrollbar-thumb {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
</style>
