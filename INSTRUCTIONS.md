# Using the FTCC Military Credit and Program Recommender (CLI)

This is a command-line application. There is no graphical interface -- every interaction
happens through the terminal, typing answers to prompts and reading printed output.

## Running it

From the project folder:

```
python main.py
```

The first time you run it (or any time the three supplied source files in source_data/
have changed), it converts them into normalized CSV files under normalized_data/ and
prints a conversion summary. Every run after that loads the existing normalized data
directly, without repeating the conversion, unless you force it:

```
python main.py --refresh
```

--refresh reconverts from the source files even if the normalized data already looks
current -- use it if you've replaced or edited a source file and want to make sure the app
picks up the change immediately rather than waiting for its own change detection to notice.

## The interactive flow

After loading or converting, the program walks you through four steps:

**1. Enter your MOS.** Type a full or partial MOS code or job title (e.g. 12P, or part of
a title like "Power"). If more than one MOS matches, you'll see a numbered list to pick
from. You can add more than one MOS -- after the first is entered, you're asked "Add
another MOS?" (y/n) -- since a veteran may hold more than one MOS by the time they leave
service (e.g. after reclassification to a different job).

**2. Enter your skill level.** For each MOS you add, you'll be shown the skill levels that
exist for it (e.g. 10, 20, 30, 40) and asked to enter one. See "Understanding skill levels
and rank" below for what these numbers actually mean.

**3. Select your completed trainings.** You'll see a menu of branches (ARMY, COAST GUARD,
MARINES, NATIONAL GUARD, NAVY). Pick a branch to see its list of trainings, then enter the
number(s) of any you've completed, separated by commas (or press Enter to select none from
that branch). After each branch, you're returned to the branch menu so you can pick another
branch or select "Done" to finish. Selections accumulate across every branch you visit.

**4. Review your results.** The program prints:
- A **Potential Credit Summary** -- every course you may have credit for, with its title,
  credit value, and which MOS or training granted it.
- The **top 3 recommended FTCC programs**, ranked by how many of your courses count toward
  each program's requirements, with an explanation of how each matched course applies
  (a required course vs. one option within a choice group) and an estimated match
  percentage.
- A report file is also saved to student_reports/, containing the same information in a
  plain-text format you can open, print, or share.

**Navigating:** at any prompt, type back to return to the previous step and change an
earlier answer, or exit to quit immediately without generating a report.

**Important:** every result is an unofficial estimate based on the supplied source
documents. It does not guarantee that credit will be awarded, and it does not replace an
official transcript evaluation or degree audit -- see the notice printed at the end of every
run and report.

## Understanding skill levels and rank

The 4th character of a 5-character MOS code (MOSC) is the **skill level** -- it tells you
how far a soldier has progressed within their MOS, not just what their job is. It's shown as
a two-digit number ending in 0 (10, 20, 30, 40, 50) in the source data this app reads, e.g.
13B10 means MOS 13B at skill level 1.

This matters when using the app because the skill level you enter changes *which* courses
you get credit for -- a soldier at a higher skill level has typically completed more
technical/leadership training, so higher skill levels generally unlock more (or different)
course equivalencies than entry-level ones for the same MOS. Picking the wrong skill level
means the app compares you against the wrong slice of your MOS's training record.

Source: **DA Pam 611-21, Chapter 10 Section C** (api.army.mil), which lays out MOSC
skill-level suffixes and their corresponding duties in full.

| Skill Level | MOSC suffix | Pay Grade(s) | Rank(s) | General Role |
|---|---|---|---|---|
| SL1 | X10 | E-1 to E-4 | PVT (E-1), PV2 (E-2), PFC (E-3), SPC/CPL (E-4) | Entry-level; individual/team-member tasks, operates and maintains assigned equipment |
| SL2 | X20 | E-5 | SGT | Team/squad-level leader; supervises SL1 Soldiers, adds technical/tactical guidance duties |
| SL3 | X30 | E-6 | SSG | Section/squad leader; plans and directs subordinate elements, more autonomous technical authority |
| SL4 | X40 | E-7 | SFC | Platoon sergeant / senior technical NCO; assists platoon leader, supervises multiple subordinate elements, training plans |
| SL5 | X50 | E-8 | 1SG / MSG | Principal NCO at company level or senior technical authority; some MOS cap here as "MOS Immaterial" once a Soldier becomes 1SG |
| SL6 | varies -- often a distinct capper MOS (e.g. 11Z, 13Z, 92Z) | E-9 | SGM / CSM | Career-management-field-wide senior enlisted advisor; many CMFs "cap" into a single CMF-wide MOS at this level rather than staying in the original MOS designator |

Full E-1 through E-9 pay grade scale, for reference:

| Pay Grade | Rank | Abbreviation |
|---|---|---|
| E-1 | Private | PVT |
| E-2 | Private Second Class | PV2 |
| E-3 | Private First Class | PFC |
| E-4 | Specialist / Corporal | SPC / CPL |
| E-5 | Sergeant | SGT |
| E-6 | Staff Sergeant | SSG |
| E-7 | Sergeant First Class | SFC |
| E-8 | Master Sergeant / First Sergeant | MSG / 1SG |
| E-9 | Sergeant Major / Command Sergeant Major / Sergeant Major of the Army | SGM / CSM / SMA |

E-8 and E-9 each split into two rank titles at the same pay grade -- MSG vs. 1SG (E-8), and
SGM vs. CSM (E-9) -- the difference is duty position (staff/technical track vs. command
track), not pay. SMA (Sergeant Major of the Army) is also E-9 but is a single nominative
position, not a duty-position split like CSM/SGM.

This table is reference documentation only -- the application itself doesn't display it
during a run or use it in any matching/scoring logic. It's here so a user (or anyone
reviewing this project) can understand what a "skill level" prompt is actually asking for
without needing to look it up elsewhere.

## Where things end up

- normalized_data/ -- the converted source data (regenerated automatically; safe to delete
  and let the app rebuild it via --refresh)
- conversion_issues/ -- any rows the importers couldn't safely interpret, for review
- student_reports/ -- your exported recommendation reports (one per run)
- logs/app.log -- a running log of conversion decisions, selections, and results (never
  includes your name or any personally-identifying information)
