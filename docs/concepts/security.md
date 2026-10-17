---
group: Concepts
order: 80
nav: Security
description: what a surface cannot do, what the user grants, and what is left to the program
---

# Security

A host treats every document as untrusted, so a surface shows only what
the program sent, and reports only what the user did. The markup comes
from the program's side of the pty, which may be a remote machine, or a
file someone `cat`s ([§12](../../SPEC.md#12-security)).

Anything that writes to the terminal can send a document. So the host
keeps the rules below, whoever sent the markup.

## What a surface cannot do

A surface has no script, no network of its own and nowhere to go. A host
makes sure that:

- **no script runs**: no `<script>`, no event-handler attributes, no
  `javascript:` URLs, and no script inside SVG;
- **nothing is fetched** but the program's own resources (`cid:`),
  `data:` URLs, and what the network policy allows, from attributes and
  CSS alike;
- **nothing navigates**: links, forms and `<meta http-equiv=refresh>` do
  nothing but send events;
- **nothing opens** a window, a dialog or a popup;
- **the keyboard stays put**: `autofocus` takes nothing, and only the user
  or the program gives a surface the keyboard;
- **nothing draws outside the rectangle**, `position: fixed` included;
- **nothing is read**: not the screen, the clipboard or other surfaces,
  and nothing of the terminal beyond the host stylesheet
  ([§8](../../SPEC.md#8-the-host-stylesheet)).

Prefetch hints and nested documents, such as `<iframe>`, are never
fetched. A surface also has no cookies and no storage
([§1](../../SPEC.md#non-goals)). Events carry only the program's own ids
and what the user entered into its surface.

## Links and forms

A link is an event, and the program decides where it goes
([Input](input.md#links)). A click sends the link's `href` and its
resolved `url`, and nothing loads. A form's `submit` sends its fields to
the program, and nowhere else.

The one link that opens without the program is a hyperlink, with
`target="_blank"` ([§9](../../SPEC.md#9-events)). The terminal opens it as
it opens an OSC 8 hyperlink in the cells, outside the surface. The same
gesture opens it, and the user's settings apply: the schemes it opens, a
confirmation, or hyperlinks turned off.

So a surface can open no link that its program could not print in the
cells. `<base href>` only sets the base URL that links resolve against
([§7.3](../../SPEC.md#73-the-base-url)): it grants nothing.

## The network is the user's to grant

A surface fetches nothing from the network unless the host and the
document both allow it ([§7.2](../../SPEC.md#72-the-network)). Every
fetch tells a server that the document is being shown, and where. That is
the user's decision, so a terminal should start with an empty policy.

The policy has two halves, and a URL is fetched only when both allow it:

- **The host's half** is set by the user, or by the page that embeds the
  host. It lists sources for each directive: `img-src`, `media-src`,
  `font-src` and `style-src`. A source is an origin, or `https:` for every
  HTTPS origin.
- **The document's half** says what it needs, in CSP's syntax. A
  document with none asks for nothing.

```text
host    → ESC ] 7279 ; a=ok:n=1:re=q ; {"v": "0.4", …, "net": {"img-src": ["https://example.com"]}} ST
program → ESC ] 7279 ; a=doc:s=post ; <meta name="hotty-network" content="img-src https://example.com"> <img src="https://example.com/cover.png"> ST
```

The host reports its half as `net` in its capabilities, so a program
knows what it may ask for. A document never gets more than the host
allows. A reference the policy refuses fails as a missing resource does.

A host should send no referrer and no credentials with what it fetches.
[Images and the network](resources.md) says how a document uses what it is
granted.

## What a host checks

A host should keep these rules with two independent layers, so that when
one misses, the other still holds ([§12](../../SPEC.md#12-security)):

- a **sanitizer** removes what can run, navigate or load, before the
  markup reaches a live document;
- an **engine or policy** cannot fetch beyond the network policy,
  whatever the sanitizer missed.

The second layer has to hold on its own. A sanitizer that reads
attributes misses the requests CSS carries: `url()`, `@import` and
`@font-face`.

A host built on a web engine inherits the policies of the page that
embeds it, and its documentation says what that page must allow.
xterm-addon-hotty, for one, draws each surface in a sandboxed iframe
([Choose a host](../hosts.md#a-browser)).

A host also guards the terminal itself
([§13](../../SPEC.md#13-limits)). It refuses what would pass its limits
with `EQUOTA`, and drops a message that is too large. It may abandon a
render that runs past its time budget, with `EBUDGET`, so that no
document stalls the terminal.

## What a program still does

The host keeps a document from doing harm, but it cannot know what the
program meant. A few things stay yours:

- **Escape text you did not write.** A host cannot tell your markup from
  text you put into it. Unescaped, that text can add a link, a form or a
  request for the network that you did not mean.
- **Open links as a terminal would.** A program that opens a link's `url`
  itself takes on a terminal's job for a hyperlink. It decides which
  schemes to open, and whether to ask first.
- **Detach what you leave on the screen.** Events reach whatever reads
  the terminal's input next, and a shell reads them as typing. Create the
  documents you leave detached, or detach them before you exit
  ([§5.5](../../SPEC.md#55-ownership-adetach)).
- **Leave no answer behind.** Read the replies your commands caused
  before you exit, and withdraw a query that asked for a late answer
  ([Degrading](degrading.md#a-late-answer)).
- **Show a secret only where you would print it.** A surface's text is
  terminal output. It stays in the scrollback with its line, and a host
  should search and copy it as it does the cells' text
  ([§11](../../SPEC.md#11-text)).

A detached surface sends no events, and its form controls are disabled.
Its hyperlinks still open, since they are the terminal's.
