# BinderScan

Scan Magic: The Gathering binder pages (1, 4, 9 or 12 pockets) or single cards with your phone, review every card (foil / exact printing), and keep a collection valued with Cardmarket prices.

## Put it on your phone (5 minutes, free)
The app needs to be served over HTTPS for the camera and "Add to Home Screen" to work.

**Netlify Drop (easiest)**
1. On a computer, open https://app.netlify.com/drop
2. Drag the unzipped `binderscan` folder onto the page.
3. Open the URL it gives you on your phone.
4. iPhone: Share → Add to Home Screen. Android (Chrome): ⋮ → Install app.

**GitHub Pages** works too: push the folder to a repo, Settings → Pages → deploy from branch.

## How it works
- **Scan**: pick the binder layout, take a photo, drag the four corners onto the outer card edges (the photo is flattened, so slight angles are fine).
- **Review**: every card is listed before saving. Toggle **Foil**, tap **Version** to choose the exact printing (with its price), **Search** to fix a misread, set quantity or skip empty pockets.
- **Recognition**: on-device OCR reads the name line and the set code + collector number bottom-left (works for German cards). For better accuracy on glossy sleeves, add an Anthropic API key in Settings and switch to Claude vision.
- **Prices**: Cardmarket trend prices in EUR via Scryfall (free, updated daily). Cardmarket isn't accepting new API applications, so per-country cheapest offers can't be fetched automatically; each card has a "Cheapest from Germany" button opening Cardmarket filtered to German sellers, and you can save that price as your own.
- **Data** stays on your phone (browser storage). Use Export backup regularly; CSV export is included.
