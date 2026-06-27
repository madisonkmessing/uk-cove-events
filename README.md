# UK Cove — Weekly Events Feed

This folder makes the "happening this week" events feed for UK Cove update
itself automatically, every Sunday at 8:00 PM, for free — using GitHub.

You don't need to know how to code to set this up. Follow these steps once,
and it runs itself after that.

## What's in here

- `weekly_events.py` — the script that checks Campus Rec, UK Athletics,
  and VisitLex, scores the events, and picks the best ones.
- `docs/index.html` — the webpage that displays the results. This is what
  you'll point Wix at.
- `.github/workflows/weekly_events.yml` — the instructions that tell GitHub
  "run the script every Sunday at 8pm."

## One-time setup (about 10 minutes)

1. **Create a new repository on GitHub** (or ask whoever manages your
   family's GitHub to create one for you). Name it something like
   `uk-cove-events`.

2. **Upload these files into it**, keeping the folder structure exactly as
   they are (the `.github` and `docs` folders need to stay where they are —
   don't flatten everything into one folder).

3. **Turn on GitHub Pages:**
   - In the repository, click **Settings**.
   - Click **Pages** in the left sidebar.
   - Under "Build and deployment," set **Source** to "Deploy from a branch."
   - Set the branch to `main` (or whichever branch you uploaded to) and the
     folder to `/docs`.
   - Click **Save**.
   - GitHub will give you a web address, something like:
     `https://yourusername.github.io/uk-cove-events/`
   - **Save that address** — that's the one you'll paste into Wix.

4. **Turn on GitHub Actions** (it's usually on by default, but double check):
   - Click the **Actions** tab in the repository.
   - If it asks you to enable workflows, click the button to enable them.

5. **Test it once manually** (don't wait until Sunday):
   - Click the **Actions** tab.
   - Click **Weekly UK Cove Events Pull** in the left list.
   - Click the **Run workflow** button, then **Run workflow** again to confirm.
   - Wait about a minute, then refresh — you should see a green checkmark
     if it worked, or a red X with an error message if something needs fixing.

6. **Check the live page:**
   - Visit the address from step 3 in your browser.
   - You should see this week's events.

## Connecting it to Wix (Cove)

1. In the Wix Harmony editor, find the **Embed Code** or **HTML iFrame**
   element (usually under an "Embed" or "More" section when adding elements).
2. Choose **Embed a site / URL**.
3. Paste in the GitHub Pages address from step 3 above.
4. Resize it to fit your page.
5. Publish.

## A note on the schedule

GitHub runs schedules using UTC time, not your local time. The included
workflow is set for Sunday 8:00 PM **Eastern Daylight Time** (summer).
When the U.S. switches to Eastern Standard Time (winter), the line in
`weekly_events.yml` needs to shift by one hour. This is a one-line edit —
ask whoever manages the repo to change `cron: "0 0 * * 1"` to
`cron: "0 1 * * 1"` in late autumn, and back again in spring. (A future
improvement could automate this, but it's a once-or-twice-a-year edit.)

## If something breaks

- Check the **Actions** tab — every run is logged there, and failed runs
  show a red X with an error message you can read (or share with whoever's
  helping you with this).
- Remember: Campus Rec, UK Athletics, and VisitLex selectors were written
  based on each site's general structure, not confirmed against a live
  event. If a run fails or comes back empty, the most likely cause is that
  a site's HTML structure needs to be double-checked and the script
  adjusted to match.
