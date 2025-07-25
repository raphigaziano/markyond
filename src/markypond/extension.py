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
from markdown.preprocessors import Preprocessor

from .exceptions import MarkypondError
from .lilypond import run_lilypond
from .utils import dotdict, mkdirs_for_path, urljoin


logger = logging.getLogger(__name__)


class MarkypondPreprocessor(Preprocessor):

    SUPPORTED_OUTPUT_FORMATS = ('svg', 'png', 'pdf')

    # start line, e.g., `   {{markypond}} `
    RE_MARKY_START = re.compile(
        r'^ *\{+ *markypond *(?P<arg_list>.*?)\}+ *$',
        re.IGNORECASE)
    # end line, e.g, '{ /markypond   }'
    RE_MARKY_END = re.compile(
        r'^ *\{+ */markypond *\}+ *$',
        re.IGNORECASE)

    # single block argument
    RE_SINGLE_ARG = re.compile(
        r'(?P<arg_name>\w+?) *= *[\'"](?P<arg_val>.+?)[\'"]')

    def __init__(self, *args, **kwargs):
        self.config = {
            'cache_dir': kwargs.pop('cache_dir'),
            'output_dir': kwargs.pop('output_dir'),
            'output_fmt': kwargs.pop('output_fmt'),
            'base_url': kwargs.pop('base_url'),
        }
        super().__init__(*args, **kwargs)

    def run(self, lines):

        new_lines = []
        in_marky_block = False
        pond_src = []
        opening_match = None

        for line in lines:
            if (match := self.RE_MARKY_START.search(line)):
                opening_match = match
                in_marky_block = True
            elif self.RE_MARKY_END.search(line):
                if not in_marky_block:
                    continue
                block_args = self.parse_args(opening_match)
                tag = self.run_lilypond('\n'.join(pond_src), block_args)
                new_lines.append(tag)
                in_marky_block = False
                pond_src.clear()
            elif in_marky_block:
                pond_src.append(line)
            else:
                new_lines.append(line)

        return new_lines

    def parse_args(self, opening_match):
        arg_list = opening_match.group('arg_list')
        args = self.config.copy()
        args.update({
            m.group('arg_name'): m.group('arg_val')
            for m in self.RE_SINGLE_ARG.finditer(arg_list)
        })
        logger.debug('Markdown block arguments: %s', args)
        return dotdict(**args)

    def run_lilypond(self, src, args):

        if 'output_file' not in args:
            raise MarkypondError('output_file block argument is required.')

        # alias and check output format
        fmt = args.output_fmt
        if fmt not in self.SUPPORTED_OUTPUT_FORMATS:
            raise MarkypondError(
                f"Output format {fmt} is not supported by MarkyPond.\n"
                f"Supported formats: "
                f"{', '.join(self.SUPPORTED_OUTPUT_FORMATS)}")

        logger.info('Output format: %s', fmt)

        # lilypond file generation (cache file)
        hashed = hashlib.md5(src.encode('utf-8')).hexdigest()
        cache_file_path = f'{os.path.join(args.cache_dir, hashed)}.{fmt}'
        run_lilypond(src, cache_file_path)
        logger.info('Lilypond output cached in: %s', cache_file_path)

        # Copy generated file to destination
        output_file_path = os.path.join(args.output_dir, args.output_file)
        mkdirs_for_path(output_file_path)
        shutil.copy2(cache_file_path, output_file_path)
        logger.info(
            'Copied lilypond output to destination: %s', output_file_path)

        # Generate tag for html output
        html_tag = self.generate_tag(args)
        return etree.tostring(html_tag).decode('utf-8')

    def generate_tag(self, args):
        method_name = f'generate_tag_for_{args.output_fmt}'
        if (method := getattr(self, method_name, None)):
            return method(args)
        raise NotImplementedError(
            f'No tag generation implemented for output format {args.output_fmt}')

    def generate_tag_for_png(self, args):
        return self.generate_img_tag(args)

    def generate_tag_for_svg(self, args):
        return self.generate_img_tag(args)

    def generate_tag_for_pdf(self, args):
        return self.generate_link_tag(args)

    def generate_img_tag(self, args):
        img = etree.Element('img')
        img.set('class', 'lilypond-img')
        url = urljoin(args.base_url, args.output_file)
        img.set('src', url)
        return img

    def generate_link_tag(self, args):
        link = etree.Element('a')
        link.set('class', 'lilypond-link')
        url = urljoin(args.base_url, args.output_file)
        link.set('href', url)
        link.text = args.get('link_name', '')
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
        # Seems to work on all priorities values for now. We may need to adjust
        # this for compatibility with other extensions.
        md.preprocessors.register(
            MarkypondPreprocessor(**self.getConfigs()),
            'markypond',
            0
        )


def makeExtension(**kwargs):
    return MarkypondExtension(**kwargs)
