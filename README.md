# MarkyPond

A [Python-Markdown](https://github.com/Python-Markdown/markdown) extension to
include [lilypond](https://lilypond.org/) source in your markdown files and
generate the appropriate files from it.

## Install

From github:

```bash
python3 -m pip install git+https://github.com/raphigaziano/markypond
```

## Usage

```python
import markdown

s = '''
{markypond output_file="out.png"}
\score{
  \relative c'' {
    % some notes
    c d e f g
  }
  \layout{}
}
{/markypond}
''''

extensions = ['markypond']
extension_configs = {
    'markypond': {
        'output_dir': './static/img/lilypond',
        'base_url': 'http://mysite.com/lilypond/'
    },
}

print(markdown.markdown(s, extensions=extensions, extension_configs=extension_configs))
```

Output:

```html
<p><img src="http://mysite.com/lilypond/out.png"/></p>
```

You can also import the extenssion manually (recommended by the python-markdown
docs):

```python
import markdown
from markypond import MarkypondExtension

s = '''
{markypond output_file="out.svg"}
\score{
  \relative c'' {
    % some notes
    c d e f g
  }
  \layout{}
}
{/markypond}
''''

# with config
print(markdown.markdown(
    s, extensions=[MarkypondExtension(output_fmt='svg')]
))
```

Output:

```html
<p><img src="/out.svg"/></p>
```

For more information, see [Extensions - Python-Markdown documentation](https://python-markdown.github.io/extensions/)
and [Using Markdown as a Python Library - Python-Markdown documentation](https://python-markdown.github.io/reference/#extensions).

Block delimiters can include anynumber of curly braces and ignore whitespace,
axcept for argument separation:

```markdown
{{{ markypond   output_file="out.svg" }
  ...
{{{ /markypond }}
```

Note: said arguments values **must** be enclosed in quotes (single or double).

The `output_file` argument is mandatory.

### CLI

```bash
python3 -m markdown -x markypond input.md > output.html
python3 -m markdown -x markypond -c config.json input.md > output.html
```

For more information, see [Using Python-Markdown on the Command Line - Python-Markdown documentation](https://python-markdown.github.io/cli/).

### Pelican

[Pelican](https://blog.getpelican.com/) is a static site generator.

Edit `pelicanconf.py`, `MARKDOWN` dict variable. Example:

```python
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {
            'css_class': 'highlight',
            'linenums': False,
            'guess_lang': False,
        },
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.toc': {},

        'markypond': {
            'output_fmt': 'svg',
            'output_dir': 'output/lilypond',
            'base_url': SITE_URL + '/lilypond/',
        },
    },
    'output_format': 'html5',
}
```

For more information, see [Settings - Pelican Docs](https://docs.getpelican.com/en/stable/settings.html).

## Configuation options

- `output_dir`:

  Generated files will be copied there. Defaults to the current working
  directory.

- `output_fmt`:

  Desired output format. Supported values are 'png' (default), 'svg' and 'pdf'.

  Note: by default, pdf format will generate a link element insead of an `img`.
  The link's name can be specified via the `link_name` block argument (which
  isn't used with other formats).

  Note: generated file extensions do not have to match the actual format.

- `base_url`:

  Url prefix used in the generated html elements.

- `cache_dir`:

  All generated files are first dumped in the `cache_dir`, to avoid regerating
  a source that has already been processed. Default to `.markypond_cache`.

All of those values can be overriden at the markdown block level:

```markdown
{markypond output_file="out.pdf" output_fmt="pdf" link_name="My pdf" base_url="/lilypond/pdf/"}
```
Output:

```html
<p><a href='/lilypond/pdf/out.pdf>My pdf</a></p>
```

## Improvements

This tool was build to suit my immediate needs and I'm sure there are many
possible use cases I didn't think about. If you have some need that's not
supported, feel free to open an issue.

No guarantee though. Complex features will probably take a while.

## Acknowledgments

- This README structure was stolen from
  [Phucker's markdown_link_attr_modifier](https://github.com/Phuker/markdown_link_attr_modifier/),
  which also served as a reference on the Markdown extension API.
