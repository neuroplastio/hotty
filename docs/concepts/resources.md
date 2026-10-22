---
group: Concepts
order: 70
nav: Images and the network
description: images, fonts and stylesheets sent in-band, and the network where both sides allow it
---

# Images and the network

A surface loads what your program sends it, and from the network only what
both the host and the document allow ([§7](../../SPEC.md#7-resources)). An
image, a font or a stylesheet travels in the program's output as a
**resource**, beside the documents that use it. The network stays off
until the host's user, or the page that embeds the host, grants some of it.

## Resources

A resource is bytes with a name and a MIME type, which the host keeps for
the session ([§7.1](../../SPEC.md#71-in-band-resources)). A program sends
one with `a=res`, and a document refers to it as `cid:` and its name, as
HTML e-mail refers to its attachments:

```text
program → ESC ] 7279 ; a=res:id=logo:type=image/png ; <the PNG's bytes> ST
program → ESC ] 7279 ; a=doc:s=about ; <img src="cid:logo"> <h1>Deploys</h1> ST
```

(Payloads are shown decoded here; on the wire they are base64.)

A `cid:` reference works wherever a document names something to load:

- in the attributes `src`, `srcset` and `poster`, SVG's `href`, and the
  `href` of a `<link rel=stylesheet>`;
- in CSS `url()` and `@import`, whether in a `style` attribute, a
  `<style>` element or a stylesheet that is itself a resource.

One resource serves every surface that refers to it. A stylesheet sent
once can dress all of a program's surfaces, and a font sent once can set
all their headings.

- **Order doesn't matter.** A reference to a resource that hasn't arrived
  yet resolves when it does. A placement with `f=1` hears if that changed
  the document's height
  ([Surfaces](surfaces.md#when-the-content-changes-height)).
- **Sending it again replaces it,** and every surface that refers to it is
  drawn again. A chart drawn as an image updates this way.
- **`a=del:id=<id>`** deletes it. References to it then fail, as if it had
  never come.

A host keeps resources within a quota, which it reports as
`limits.resources`, and refuses one past it with `EQUOTA`. A resource is
one message, so the largest message a host takes, `limits.message`, is
also its largest resource. A host that limits messages should take at
least 1 MiB ([§13](../../SPEC.md#13-limits)).

A small image needs no resource. A host loads `data:` URLs too
([§12](../../SPEC.md#12-security)), and an inline `<svg>` is part of the
document.

**The program's values stand.** A host may rewrite a reference in order to
load it, to a `blob:` URL, say. Morphs and events still see the attribute
as the program wrote it: `src="cid:logo"`.

## Why in-band

Everything a surface needs comes in the program's output, so a program
behaves the same locally, over SSH and inside a container
([§1](../../SPEC.md#1-introduction)). The host never reads the program's
files, which over SSH are on another machine. A resource takes the path
the document took.

It also keeps a surface safe to show. Markup can come from anywhere, a
file someone `cat`s included, and every fetch tells a server who looked,
and from where ([Appendix B](../../SPEC.md#appendix-b-rationale)). So the
network is the user's to grant, not the document's to take.

## The network

The **network policy** decides what a surface may fetch
([§7.2](../../SPEC.md#72-the-network)). It has two halves, and a URL is
fetched only when both allow it:

- **The host's half** is set by its user, or by the page that embeds the
  host. It is empty unless they grant something, and a terminal should
  start with it empty.
- **The document's half** is what the document asks for. A document that
  asks for nothing fetches nothing.

So the host grants and the document asks. A document can only get less
than the host allows, and a host's grant fetches nothing for a document
that doesn't ask.

Each half lists **sources** for each **directive**, as a Content Security
Policy does:

| directive | covers |
| --- | --- |
| `img-src` | images: `<img>`, `srcset`, `<picture>`, `poster`, images in SVG and in CSS |
| `media-src` | `<audio>` and `<video>` |
| `font-src` | `@font-face` |
| `style-src` | stylesheets: `<link rel=stylesheet>` and `@import` |

A source is an origin, such as `https://example.com` or
`http://localhost:8080`, or `https:`, which matches every HTTPS origin. A
document asks in a `<meta>` element, in CSP's syntax:

```html
<meta name="hotty-network" content="img-src https://example.com; font-src https:">
```

The host reports its half in its capabilities, as `net`
([§4](../../SPEC.md#4-detection-and-capabilities)). Your program can read
it before it relies on a fetch, and send an image in-band where the host
grants nothing:

```text
host → ESC ] 7279 ; a=ok:n=1:re=q ; {"v": "0.5", …, "net": {"img-src": ["https://example.com"]}} ST
```

A host should fetch without a referrer and without credentials, such as
cookies. A reference the policy doesn't allow fails as a missing resource
does. What is fetched arrives after the document is laid out, so a
program that sizes a surface by its content places it with `f=1`.

Some things are never fetched, whatever the policy: prefetch and
preconnect hints, and nested documents in `<iframe>`, `<object>` or
`<embed>` ([Security](security.md)).

## The base URL

A document's relative references resolve against its base URL
([§7.3](../../SPEC.md#73-the-base-url)). That is the `href` of its first
`<base>` element, when that is an absolute `http` or `https` URL.
Otherwise it is `https://hotty.invalid/`, an address that leads nowhere.

The base URL grants nothing by itself. A relative image still needs the
network policy, and a relative link still opens nothing. Here a post
fetches its cover from its own site, on a host that grants that origin,
and the user clicks a link
([Appendix A](../../SPEC.md#appendix-a-examples)):

```text
program → ESC ] 7279 ; a=doc:s=post ; <base href="https://example.com/blog/"> <meta name="hotty-network" content="img-src https://example.com"> <img src="cover.png"> <a href="../about">About</a> ST
          (the host fetches https://example.com/blog/cover.png)
host    → ESC ] 7279 ; a=ev:s=post:e=click ; {"area": …, "href": "../about", "url": "https://example.com/about"} ST
```

A link's `click` carries `href` as the document has it, and `url`, the
`href` resolved against the base. `url` is left out when it would fall
under `https://hotty.invalid/`, so without a base, a relative link has only
its `href`. The program decides what the click means: another page of its
own, or a link for its platform to open ([Input](input.md#links)).

- **A link with `target="_blank"`** is a hyperlink. It belongs to the
  terminal, and opens at its `url` as an OSC 8 hyperlink opens. A link
  with no `url` is not one.
- **A form's empty `action`** resolves too, and goes nowhere: submitting
  it is an event, and nothing else.
