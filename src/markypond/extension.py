"""
Python markdown extension to set generate svg from lilypond source

Author: https://github.com/raphigaziano

"""
import os
import re
import logging
import xml.etree.ElementTree as etree
import hashlib
import shutil

from markdown.extensions import Extension
from markdown.blockprocessors import BlockProcessor

from .exceptions import MarkypondError
from .lilypond import run_lilypond
from .utils import mkdirs_for_path, urljoin


logger = logging.getLogger(__name__)


class MarkypondBlockProcessor(BlockProcessor):

    SUPPORTED_OUTPUT_FORMATS = ('svg', 'png', 'pdf')

    # start line, e.g., `   {{markypond}} `
    RE_SRLY_START = re.compile(
        r'^ *\{+ *markypond *(?P<arg_list>.*?)\}+ *\n?',
        re.IGNORECASE)
    # last non-blank line, e.g, '{ /markypond   }\n  \n\n'
    RE_SRLY_END = re.compile(
        r'\n *\{+ */markypond *\}+\s*$',
        re.IGNORECASE)
    # argument list in opening marker
    RE_ARG_LIST = re.compile(
        r'\{+ *markypond *(?P<arg_list>.*?)\}+',
        re.IGNORECASE)

    # single block argument
    RE_SINGLE_ARG = re.compile(
        r'(?P<arg_name>\w+?) *= *[\'"](?P<arg_val>.+?)[\'"]')

    def __init__(self, *args, **kwargs):
        self._cache_dir = kwargs.pop('cache_dir')
        self._output_dir = kwargs.pop('output_dir')
        self._output_fmt = kwargs.pop('output_fmt')
        self._base_url = kwargs.pop('base_url')
        super().__init__(*args, **kwargs)
        self.opening_match = None
        self.block_args = {}

    @property
    def output_file(self):
        return self.block_args.get('output_file')

    @property
    def cache_dir(self):
        return self.block_args.get('cache_dir', self._cache_dir)

    @property
    def output_dir(self):
        return self.block_args.get('output_dir', self._output_dir)

    @property
    def output_fmt(self):
        return self.block_args.get('output_fmt', self._output_fmt)

    @property
    def base_url(self):
        return self.block_args.get('base_url', self._base_url)

    def test(self, parent, block):
        if (m := self.RE_SRLY_START.match(block)):
            self.opening_match = m
        return m

    def run(self, parent, blocks):
        original_block = blocks[0]
        blocks[0] = self.RE_SRLY_START.sub('', blocks[0])

        self.parse_args()

        if not self.output_file:
            raise MarkypondError('output_file block argument is required.')

        for block_num, block in enumerate(blocks):

            # Find block with ending tag
            if self.RE_SRLY_END.search(block):

                fmt = self.output_fmt
                if fmt not in self.SUPPORTED_OUTPUT_FORMATS:
                    raise MarkypondError(
                        f"Output format {fmt} is not supported by MarkyPond.\n"
                        f"Supported formats: "
                        f"{', '.join(self.SUPPORTED_OUTPUT_FORMATS)}")

                logger.info('Output format: %s', fmt)

                # Remove opening block
                blocks[block_num] = self.RE_SRLY_END.sub('', block)

                # Generate cache file from lilypond
                src = "".join(blocks[0:block_num+1])
                hashed = hashlib.md5(src.encode('utf-8')).hexdigest()
                cache_file_path = (
                    f'{os.path.join(self.cache_dir, hashed)}.{fmt}')
                run_lilypond(src, cache_file_path)
                logger.info(
                    'Lilypond output cached in: %s', cache_file_path)

                # Copy generated file to destination
                output_file_path = os.path.join(
                    self.output_dir, self.output_file)
                mkdirs_for_path(output_file_path)
                shutil.copy2(cache_file_path, output_file_path)
                logger.info(
                    'Copied lilypond input to destination: %s',
                    output_file_path)

                # Generate tag for html output
                html_tag = self.generate_tag(self.output_file, fmt)
                parent.append(html_tag)

                # Remove processed blocks from the block list
                for _ in range(0, block_num + 1):
                    blocks.pop(0)

                return True

        # No closing marker:  Restore and do nothing
        blocks[0] = original_block
        return False  # equivalent to our test() routine returning False

    def parse_args(self):
        arg_list = self.opening_match.group('arg_list')
        self.block_args = {
            m.group('arg_name'): m.group('arg_val')
            for m in self.RE_SINGLE_ARG.finditer(arg_list)
        }
        logger.debug('Markdown block arguments: %s', self.block_args)

    def generate_tag(self, file_name, fmt):
        if (method := getattr(self, f'generate_tag_for_{fmt}', None)):
            return method(file_name, fmt)
        raise NotImplementedError(
            f'No tag generation implemented for output '
            f'format {fmt}')

    def generate_tag_for_png(self, file_name, fmt):
        return self.generate_img_tag(file_name, fmt)

    def generate_tag_for_svg(self, file_name, fmt):
        return self.generate_img_tag(file_name, fmt)

    def generate_tag_for_pdf(self, file_name, fmt):
        return self.generate_link_tag(file_name, fmt)

    def generate_img_tag(self, file_name, fmt):
        img = etree.Element('img')
        img.set('class', 'lilypond-img')
        url = urljoin(self.base_url, file_name)
        img.set('src', url)
        return img

    def generate_link_tag(self, file_name, fmt):
        link = etree.Element('a')
        link.set('class', 'lilypond-link')
        url = urljoin(self.base_url, file_name)
        link.set('href', url)
        link.text = self.block_args.get('link_name', '')
        return link


class MarkypondExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            'cache_dir': [
                '.markypond_cache',
                "Directory to store cache files. Default: '.markypond_cache'"],
            'output_dir': [
                '.',
                'Output directory. Default to cwd.'],
            'output_fmt': [
                'png',
                'Output format. Possible values: png, svg, pdf.'],
            'base_url': [
                '/',
                'Url prefix to be appended before the file name in html link.'
                "Defaults to '/'."],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            MarkypondBlockProcessor(parser=md.parser, **self.getConfigs()),
            'markypond',
            9999,
        )


def makeExtension(**kwargs):
    return MarkypondExtension(**kwargs)
