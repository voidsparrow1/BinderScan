# BinderScan

Scan Magic: The Gathering binder pages (1, 4, 9 or 12 pockets) or single cards, review every card (foil / exact printing), and keep a collection valued with Cardmarket prices.

## Files
Everything sits in the top level of the repo, except the one file GitHub requires in a folder:
`.github/workflows/build-index.yml` (create it with Add file → Create new file and type that full name).

## How recognition works
Cards are recognised by their **artwork**, like dedicated scanner apps do, not by reading text. A GitHub Action
(`.github/workflows/build-index.yml`) downloads every paper card image from Scryfall, stores a small fingerprint of each in
`data/index.bin` (about 4 MB), and refreshes it on the 1st and 15th of each month. The app downloads that file once and
compares every scanned card against it on your phone, then double-checks the closest candidates against their real images.

### First-time setup
1. Repo → **Actions** → enable workflows if asked.
2. **Build card index** → **Run workflow**. The first run takes about 30–60 minutes; later runs only fetch new cards.
3. When it finishes, `data/index.bin` and `data/meta.json` appear in the repo. Settings in the app then shows how many printings it knows.

If Actions can't push (error 403 in the log): Settings → Actions → General → Workflow permissions → **Read and write permissions**.

## Using it
- **Scan**: pick the layout, take a photo, drag the four corners onto the outer edges of the pockets.
- **Review**: every card is listed before saving. Toggle **Foil**, tap **Version** for the exact printing, or **Search** (type `fin 519` for set + number).
- **Prices**: Cardmarket trend prices (EUR) via Scryfall. Each card links to Cardmarket filtered to sellers in your country.
- **Data** stays on your phone. Use Export backup regularly.
