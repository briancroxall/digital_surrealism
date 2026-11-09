# Setting up a lab Mac

For whoever sets up the Macs students will use (the instructor or IT). When
you're done, a student double-clicks **Digital Surrealism** on the Desktop and
the Frame extractor opens in their web browser.

The Mac needs:

- **ffmpeg** (reads the films)
- **uv** (runs the Python code, and downloads Python itself)
- **this repo**, in a folder every account can read

Installing needs an administrator account. Students don't need one.

## 1. Check what's already installed

Open Terminal and run:

```
which brew ffmpeg uv git
```

Each tool that's installed prints a path; a missing one prints `not found`.
Skip any step below for a tool that's already there.

## 2. Install Homebrew (if missing)

Homebrew installs the other tools. Logged in as an administrator, follow the
instructions at <https://brew.sh>. At the end, the installer prints "Next
steps" with two or three commands that put `brew` on your PATH: run those
too, then close and reopen Terminal.

Check:

```
brew --version
```

## 3. Install ffmpeg and uv

```
brew install ffmpeg uv
```

Check:

```
ffmpeg -version
uv --version
```

Each should print a version number. (Homebrew puts them in `/opt/homebrew/bin`,
where every account on the Mac can run them.)

## 4. Put the repo in a shared folder

`/Users/Shared` is readable by every account, so the repo goes there:

```
cd /Users/Shared
git clone https://github.com/briancroxall/digital_surrealism.git
```

Check that the launcher is there and marked as runnable (the line should
start with `-rwxr-xr-x`):

```
ls -l "/Users/Shared/digital_surrealism/lab/Digital Surrealism.command"
```

Students never write into this folder. Each account keeps its own copy of
Python and Flask in `~/Library/Caches/digital-surrealism/`, which the launcher
creates on first use.

## 5. Put the launcher on the Desktop

In Finder, open `/Users/Shared/digital_surrealism/lab`. Hold **Option** and
**Command** and drag **Digital Surrealism.command** to the Desktop. This makes
an alias (the icon gets a small arrow). Rename it "Digital Surrealism" if you
like.

Use an alias, not a copy: the launcher finds the code by looking in the
folder it lives in, so a copy on the Desktop can't find it. (It says so if
that happens.)

Desktops belong to each account, so each account needs its own alias.

## 6. Test it

Log in as an ordinary (non-administrator) account, ideally one a student
would use.

1. Double-click **Digital Surrealism** on the Desktop. A Terminal window
   opens.
2. The first time on each account, it says "First time on this Mac account:
   setting up" and downloads Python (about 27 MB) and Flask. This took a few
   seconds on a fast connection; a slow network will take longer.
3. The extractor opens in the web browser at `http://127.0.0.1:5150`.
4. Choose a film and run through the steps. The first time, macOS may ask
   whether Terminal can access files in a folder (for example, Documents or
   a USB drive). Click **Allow**.
5. Check that the frames folder appears where you chose to save it.
6. Quit by pressing **Control-C** in the Terminal window, then close it.

## Updating

When the code changes, on each Mac:

```
cd /Users/Shared/digital_surrealism
git pull
```

Each account picks up the changes the next time the launcher runs.

## Troubleshooting

**"ffmpeg isn't installed on this Mac" (or uv).** Repeat steps 1–3. The
launcher looks in `/opt/homebrew/bin`, `/usr/local/bin`, and `~/.local/bin`.

**"This launcher has to stay in the lab folder…"** The Desktop icon is a
copy, not an alias. Delete it and redo step 5.

**Double-clicking opens the file in a text editor, or says it doesn't have
permission.** The launcher lost its "runnable" setting. Run:

```
chmod +x "/Users/Shared/digital_surrealism/lab/Digital Surrealism.command"
```

**"Apple could not verify… is free of malware."** This happens if the repo
was downloaded as a ZIP file instead of with `git clone`. Re-do step 4 with
`git clone`, or Control-click the launcher, choose **Open**, and confirm.

**The Terminal window opens but no browser page appears.** Open a browser and
go to `http://127.0.0.1:5150`.

**"The extractor is already running."** It's already open in another
Terminal window; the launcher just reopens the page. Use that window to quit.

**The Terminal window fills with lines like `"GET /api/status HTTP/1.1"
200`.** That's normal: it's the page checking on progress.

**The Terminal window shows a red "WARNING: This is a development server…"**
That's normal: the warning is aimed at public websites, and this server can
only be reached from this Mac.
