# Sleevescope

_(formerly BinderScan; the repository and web address keep the old name so installs and saved data carry over)_

Scan Magic: The Gathering binder pages (1, 4, 9 or 12 pockets) or single cards, review every card (foil / exact printing), and keep a collection valued with Cardmarket prices.

## Files
Everything sits in the top level of the repo, except the one file GitHub requires in a folder:
`.github/workflows/build-index.yml` (create it with Add file → Create new file and type that full name).

## How recognition works
No grid and no text reading. Take a photo of any number of cards (a binder page, a few cards on the table, one card):

1. **Find**: the app straightens the photo, looks for card-shaped outlines, and confirms each one by checking that its
   artwork matches a real card. On binder pages it also checks every spot of the grid the confirmed cards form,
   which catches cards with weak edges (black border on a black pocket, glare).
2. **Check**: you see the outlines on the photo. Tap one to leave it out, drag a corner to fix it, or "Add a card"
   and tap a card that was missed. Dashed outlines weren't recognised for sure.
3. **Match**: each card's artwork fingerprint is compared with every paper printing on Scryfall.
4. **Review**: Foil, Version, Search (e.g. `fin 519`) and quantity, then add to a binder.

The fingerprint (v2) looks at a high-pass and a gradient view of the card, which ignore smooth glare and sleeve haze.
The database (`data/index2.bin`, about 5 MB) is built by the **Build card index** GitHub Action on the 1st and 15th
of each month; the app downloads it once and caches it.

### Database setup
Repo → **Actions** → **Build card index** → **Run workflow** (about 15 minutes for a full build).
If Actions can't push (error 403 in the log): Settings → Actions → General → Workflow permissions → **Read and write permissions**.

The **Diagnostics** workflow only exists for debugging recognition; it writes card data to a separate `diag` branch.

## Using it
- **Wants**: a separate tab for cards you still need, in as many named lists as you like (e.g. per deck). Shows the cost to buy, whether you already own a card, and "Got it" moves a card into your collection. "Copy for Cardmarket" copies the list in Cardmarket's wants format to paste into a Cardmarket wants list: `4 Card Name` for any version, `1 Card Name (V.2) (Set: Extras)` for a specific printing (from `data/cm.json`, built by the same GitHub job from Cardmarket's public catalogue and MTGJSON).
- **Add without a photo**: Scan tab → "Add a card without a photo" (or "+ Add another card" in the review list). Search by name, or type set + number like `fin 519` for the exact printing.
- **Prices**: Cardmarket trend prices (EUR) via Scryfall. Each card links to Cardmarket filtered to sellers in your country.
- **Data** stays on your phone. Use Export backup regularly.
