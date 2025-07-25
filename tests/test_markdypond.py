import shutil
import re
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import markdown

from markypond.exceptions import MarkypondError


LILYPOND_SRC_SIMPLE = r'''
\score{
  \relative c'' {
    % some notes
    c d e f g
  }
  \layout{}
}'''
LILYPOND_SRC_HASH = '892897f8289a8ee303e506e3ce18b8cc'

LILYPOND_SRC_INVALID = ' <gibberish!'


class BaseTestCase(TestCase):
    """ Base TestCase with various helpers. """

    TEST_CACHE_DIR = Path('tests/markypond_cache')
    TEST_OUTPUT_DIR = Path('tests/generated_imgs')

    MOCK_DEFAULT = True

    RE_IMG_SRC = re.compile(
        r'<img.*src=[\'"](?P<src_url>.*?)[\'"].*/ ?>')

    RE_LINK_HREF = re.compile(
        r'<a.*href=[\'"](?P<href_url>.*?)[\'"].*>')

    def tearDown(self):
        """ Delete generated test files after each test. """
        try:
            shutil.rmtree(self.TEST_CACHE_DIR, ignore_errors=True)
            shutil.rmtree(self.TEST_OUTPUT_DIR, ignore_errors=True)
        except FileNotFoundError:
            pass

    def md(self, source, **config_overrides):
        """
        Helper to create a markdown parser and convert the passed md source.

        Passing mock (bool) in the arguments will skip the actual lilyond
        generation to speed up tests that don't need actual files to be
        generated. (Defaults to True).
        """
        config = {
            'cache_dir': self.TEST_CACHE_DIR,
            'output_dir': self.TEST_OUTPUT_DIR,
        }
        config.update(config_overrides)
        md = markdown.Markdown(
            extensions=['markypond', 'extra'],
            extension_configs={
                'markypond': config,
            })
        return md.convert(source)

    def mk_markyblock(self, pond_source, **kwargs):
        """
        Convenience helper to auto enclose `pond_source` with markydown markup,
        including passed arguments.
        """
        arg_str = ' '.join(
            f'{k}="{v}"' for k, v in kwargs.items())
        return f'{{markypond {arg_str}}}\n{pond_source}\n{{/markypond}}\n'

    def get_img_src(self, html):
        """
        Convenience helper to retrieve image path from an img src attribute.
        """
        m = self.RE_IMG_SRC.search(html)
        return m.group('src_url') if m else None

    def get_img_filename(self, html):
        """
        Convenience helper to retrieve image filename from an img src
        attribute.
        """
        url = self.get_img_src(html)
        return url.split('/')[-1] if url else None

    def get_link_href(self, html):
        """
        Convenience helper to retrieve image path from a link href attribute.
        """
        m = self.RE_LINK_HREF.search(html)
        return m.group('href_url') if m else None

    def get_link_filename(self, html):
        """
        Convenience helper to retrieve image filename from a link href
        attribute.
        """
        href = self.get_link_href(html)
        return href.split('/')[-1] if href else None

    def get_cache_file_path(self, fmt, dir_=None):
        """
        Convenience helper to retrieve the full path of a cache file.
        Note: this will only work with the SRC_SIMPLE case.
        """
        dir_ = dir_ or self.TEST_CACHE_DIR
        return f'{Path(dir_) / LILYPOND_SRC_HASH}.{fmt}'


class LilypondTests(BaseTestCase):
    """ Tests for basic lilypond use. """

    MOCK_DEFAULT = False

    def test_simple_case_png(self):
        source = self.mk_markyblock(LILYPOND_SRC_SIMPLE, output_file='out.png')
        result = self.md(source, output_fmt='png')
        self.assertIn('<img class="lilypond-img"', result)

        cache_file_path = self.TEST_CACHE_DIR / f'{LILYPOND_SRC_HASH}.png'
        self.assertTrue(cache_file_path.exists())

        output_file_path = self.TEST_OUTPUT_DIR / self.get_img_filename(result)
        self.assertTrue(output_file_path.exists())

    def test_simple_case_svg(self):
        source = self.mk_markyblock(LILYPOND_SRC_SIMPLE, output_file='out.svg')
        result = self.md(source, output_fmt='svg')
        self.assertIn('<img class="lilypond-img"', result)

        cache_file_path = self.TEST_CACHE_DIR / f'{LILYPOND_SRC_HASH}.svg'
        self.assertTrue(cache_file_path.exists())

        output_file_path = self.TEST_OUTPUT_DIR / self.get_img_filename(result)
        self.assertTrue(output_file_path.exists())

    def test_simple_case_pdf(self):
        source = self.mk_markyblock(
            LILYPOND_SRC_SIMPLE, output_file='out.pdf', link_name='my pdf')
        result = self.md(source, output_fmt='pdf')
        self.assertIn('<a class="lilypond-link"', result)
        self.assertIn('>my pdf</a>', result)

        cache_file_path = self.TEST_CACHE_DIR / f'{LILYPOND_SRC_HASH}.pdf'
        self.assertTrue(cache_file_path.exists())

        output_file_path = self.TEST_OUTPUT_DIR / self.get_link_filename(result)
        self.assertTrue(output_file_path.exists())

    def test_invalid_lilypond_source(self):
        source = self.mk_markyblock(
            LILYPOND_SRC_INVALID, output_file='out.png')
        with self.assertRaisesRegex(MarkypondError, "syntax error"):
            self.md(source)


@patch('os.makedirs')
@patch('shutil.copy2')
@patch('markypond.extension.run_lilypond')
class ParserTests(BaseTestCase):
    """ Tests for the markdown marker syntax. """

    def test_marker_random_whitespace(self, _, __, ___):
        result = self.md(
            f'  {{ markypond output_file =  "lol.png" }}  \n'
            f'{LILYPOND_SRC_SIMPLE}\n'
            f'{{/markypond    }}')
        self.assertIn('<img class="lilypond-img"', result)

    def test_marker_no_newlines(self, _, __, ___):
        result = self.md(
            f'{{\nmarkypond output_file="lol.png" }}\n'
            f'{LILYPOND_SRC_SIMPLE}\n'
            f'{{/markypond}}')
        self.assertNotIn('<img class="lilypond-img"', result)

        result = self.md(
            f'{{markypond output_file="lol.png" }}\n'
            f'{LILYPOND_SRC_SIMPLE}\n'
            f'{{/markypond\n}}')
        self.assertNotIn('<img class="lilypond-img"', result)

    def test_marker_several_brackets(self, _, __, ___):
        result = self.md(
            f'{{{{{{markypond output_file="lol.png" }}}}'
            f'\n{LILYPOND_SRC_SIMPLE}\n'
            f'{{{{/markypond}}')
        self.assertIn('<img class="lilypond-img"', result)

    def test_marker_case_ignored(self, _, __, ___):
        result = self.md(
            f'{{MARKYPOND output_file="LOL.png" }}'
            f'\n{LILYPOND_SRC_SIMPLE}\n'
            f'{{/MarkyPond}}')
        self.assertIn('<img class="lilypond-img"', result)

    def test_several_blocks(self, _, __, ___):
        result = self.md(
            f'{{markypond output_file="first.png" }}\n'
            f'{LILYPOND_SRC_SIMPLE}\n'
            f'{{/markypond}}\n'
            f'{{markypond output_file="second.svg" output_fmt="svg" }}\n'
            f'dummy src\n'
            f'{{/markypond}}')
        self.assertIn('src="/first.png"', result)
        self.assertIn('src="/second.svg"', result)

    def test_compat_with_attr_list_extension(self, _, __, ___):
        result = self.md(
            f'{{markypond output_file="first.png" }}\n'
            f'{LILYPOND_SRC_SIMPLE}\n'
            f'{{/markypond}}\n'
            f'{{ #test-id .test-class title="test-title"}}')
        self.assertIn(
            '<p class="test-class" id="test-id" title="test-title', result)


@patch('os.makedirs')
@patch('shutil.copy2')
@patch('markypond.extension.run_lilypond')
class ConfigTests(BaseTestCase):
    """ Tests for extension config. """

    def test_output_fmt(self, _, mocked_cp, __):
        source = self.mk_markyblock(LILYPOND_SRC_SIMPLE, output_file='out.pdf')
        self.md(source, output_fmt='pdf')
        mocked_cp.assert_called_once_with(
            self.get_cache_file_path('pdf'),
            f'{self.TEST_OUTPUT_DIR}/out.pdf')

    def test_invalid_format(self, _, __, ___):
        with self.assertRaisesRegex(
            MarkypondError, "Output format qsdf is not supported"
        ):
            source = self.mk_markyblock(
                LILYPOND_SRC_SIMPLE, output_file='out.png')
            self.md(source, output_fmt='qsdf')

    def test_output_dir(self, _, mocked_cp, __):
        for expected_output_dir in ('/abs/path', 'rel/path', './dot/path'):
            source = self.mk_markyblock(
                LILYPOND_SRC_SIMPLE, output_file='out.png')
            self.md(source, output_dir=expected_output_dir)
            mocked_cp.assert_called_with(
                self.get_cache_file_path('png'),
                f'{expected_output_dir}/out.png')

    def test_base_url(self, _, __, ___):
        source = self.mk_markyblock(LILYPOND_SRC_SIMPLE, output_file='out.png')
        result = self.md(source, base_url='/lol/wut/')
        img_src = self.get_img_src(result)
        self.assertTrue(img_src.startswith('/lol/wut/'))

        # trailing slash or not should not matter
        source = self.mk_markyblock(LILYPOND_SRC_SIMPLE, output_file='out.png')
        result = self.md(source, base_url='/lol/wut')
        img_src = self.get_img_src(result)
        self.assertTrue(img_src.startswith('/lol/wut/'))


@patch('os.makedirs')
@patch('shutil.copy2')
@patch('markypond.extension.run_lilypond')
class ArgumentsTests(BaseTestCase):
    """ Tests for markdown block arguments. """

    def test_output_filename(self, _, mocked_cp, __):
        for basename in (
            'foo.png',
            'bar.lol',  # mismatched with actual format: this is allowed
            'contains-dash.png',
            'no_extension',
            'sub/folder/out.png',
            '/abs/path/out.png'
        ):
            output_file_name = f"{basename}.png"
            source = self.mk_markyblock(
                LILYPOND_SRC_SIMPLE, output_file=output_file_name)
            self.md(source)
            mocked_cp.assert_called_with(
                self.get_cache_file_path('png'),
                f'{self.TEST_OUTPUT_DIR / output_file_name}')

    def test_no_provided_output_file_argument_is_an_arror(self, _, __, ___):
        source = self.mk_markyblock(LILYPOND_SRC_SIMPLE)
        with self.assertRaisesRegex(MarkypondError, 'output_file.*required'):
            self.md(source)

    def test_output_dir_override(self, _, mocked_cp, __):
        source = self.mk_markyblock(
            LILYPOND_SRC_SIMPLE,
            output_file='out.png',
            output_dir='some/other/dir')
        self.md(source)
        mocked_cp.assert_called_once_with(
            self.get_cache_file_path('png'), 'some/other/dir/out.png')

    def test_output_fmt_override(self, _, mocked_cp, __):
        for fmt in ('svg', 'png', 'pdf'):
            source = self.mk_markyblock(
                LILYPOND_SRC_SIMPLE,
                output_file='out.png',
                output_fmt=fmt)
            self.md(source)
            # cache file indicates the actual format via its e"xtension.
            # The output filename doesn"t *have* to reflect it.
            mocked_cp.assert_called_with(
                self.get_cache_file_path(fmt),
                f'{self.TEST_OUTPUT_DIR / "out.png"}')

    def test_base_url_override(self, _, __, ___):
        source = self.mk_markyblock(
            LILYPOND_SRC_SIMPLE,
            output_file='out.png',
            base_url='custom/url/')
        result = self.md(source)
        img_src = self.get_img_src(result)
        self.assertTrue(img_src.startswith('custom/url/'))

        # trailing slash or not should not matter
        source = self.mk_markyblock(
            LILYPOND_SRC_SIMPLE,
            output_file='out.png',
            base_url='custom/url')
        result = self.md(source)
        img_src = self.get_img_src(result)
        self.assertTrue(img_src.startswith('custom/url/'))

    def test_cache_dir_override(self, _, mocked_cp, __):
        source = self.mk_markyblock(
            LILYPOND_SRC_SIMPLE,
            output_file='out.png',
            cache_dir='my/custom/cache/dir')
        self.md(source)
        mocked_cp.assert_called_once_with(
            f'my/custom/cache/dir/{LILYPOND_SRC_HASH}.png',
            f'{self.TEST_OUTPUT_DIR / "out.png"}')

    def test_override_all_the_things(self, _, mocked_cp, __):
        source = self.mk_markyblock(
            LILYPOND_SRC_SIMPLE,
            output_file='custom-filename.invalid_but_allowed_extension',
            output_dir='foo/bar',
            output_fmt='svg',
            base_url='/custom/url',
            cache_dir='foo/cache')
        result = self.md(source)
        mocked_cp.assert_called_once_with(
            f'foo/cache/{LILYPOND_SRC_HASH}.svg',
            'foo/bar/custom-filename.invalid_but_allowed_extension')
        img_src = self.get_img_src(result)
        self.assertTrue(img_src.startswith('/custom/url/'))
