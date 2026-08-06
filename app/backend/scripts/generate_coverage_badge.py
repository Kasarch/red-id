import argparse
import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('coverage_xml', type=Path)
    parser.add_argument('output_svg', type=Path)
    parser.add_argument('--junit-xml', type=Path)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()

    coverage = _coverage_percent(args.coverage_xml)
    args.output_svg.write_text(_badge_svg(coverage), encoding='utf-8')

    if args.summary is not None:
        if args.junit_xml is None:
            parser.error('--junit-xml is required with --summary')
        passed = _passed_tests(args.junit_xml)
        with args.summary.open('a', encoding='utf-8') as summary:
            summary.write(
                '## Backend CI\n\n'
                '| Result | Tests passed | Coverage | Report |\n'
                '| --- | ---: | ---: | --- |\n'
                f'| Passed | {passed} | {coverage}% | `backend-coverage` artifact |\n'
            )


def _coverage_percent(path: Path) -> Decimal:
    root = _xml_root(path)
    line_rate = root.get('line-rate')
    if line_rate is None:
        raise ValueError('coverage XML does not contain line-rate')
    try:
        rate = Decimal(line_rate)
    except InvalidOperation as error:
        raise ValueError('coverage XML contains an invalid line-rate') from error
    if not Decimal(0) <= rate <= Decimal(1):
        raise ValueError('coverage line-rate must be between 0 and 1')
    return (rate * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def _passed_tests(path: Path) -> int:
    root = _xml_root(path)
    suites = [root] if root.tag == 'testsuite' else list(root.findall('testsuite'))
    if not suites:
        raise ValueError('JUnit XML does not contain a testsuite')
    tests = sum(_integer_attribute(suite, 'tests') for suite in suites)
    failures = sum(_integer_attribute(suite, 'failures') for suite in suites)
    errors = sum(_integer_attribute(suite, 'errors') for suite in suites)
    skipped = sum(_integer_attribute(suite, 'skipped') for suite in suites)
    return tests - failures - errors - skipped


def _integer_attribute(root: ET.Element, name: str) -> int:
    value = root.get(name)
    if value is None:
        raise ValueError(f'JUnit XML does not contain {name}')
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f'JUnit XML contains an invalid {name}') from error


def _xml_root(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError(f'cannot read valid XML from {path}') from error


def _badge_svg(coverage: Decimal) -> str:
    color = _coverage_color(coverage)
    label = f'{coverage}%'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="116" height="20" role="img" '
        'aria-label="coverage: '
        f'{label}">'
        '<title>coverage: '
        f'{label}</title>'
        '<linearGradient id="s" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/>'
        '</linearGradient>'
        '<clipPath id="r"><rect width="116" height="20" rx="3"/></clipPath>'
        '<g clip-path="url(#r)"><rect width="70" height="20" fill="#555"/>'
        f'<rect x="70" width="46" height="20" fill="{color}"/>'
        '<rect width="116" height="20" fill="url(#s)"/></g>'
        '<g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" '
        'font-size="11"><text x="35" y="15" fill="#010101" fill-opacity=".3">coverage</text>'
        '<text x="35" y="14">coverage</text>'
        f'<text x="93" y="15" fill="#010101" fill-opacity=".3">{label}</text>'
        f'<text x="93" y="14">{label}</text></g></svg>\n'
    )


def _coverage_color(coverage: Decimal) -> str:
    if coverage >= 90:
        return '#4c1'
    if coverage >= 80:
        return '#97ca00'
    if coverage >= 70:
        return '#dfb317'
    if coverage >= 60:
        return '#fe7d37'
    return '#e05d44'


if __name__ == '__main__':
    main()
