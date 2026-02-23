"""Unit 3: test parse_week_number with mock HTML."""
from bs4 import BeautifulSoup
from fantasyVCT.scraper import Scraper


def _soup(canonical_href):
    html = f'<html><head><link rel="canonical" href="{canonical_href}"/></head><body></body></html>'
    return BeautifulSoup(html, "html.parser")


def test_parse_week_number_w1():
    soup = _soup("https://www.vlr.gg/459518/team-a-vs-team-b/w1")
    assert Scraper.parse_week_number(soup) == 1


def test_parse_week_number_w2():
    soup = _soup("https://www.vlr.gg/459519/some-match/w2")
    assert Scraper.parse_week_number(soup) == 2


def test_parse_week_number_double_digit():
    soup = _soup("https://www.vlr.gg/459520/some-match/w12")
    assert Scraper.parse_week_number(soup) == 12


def test_parse_week_number_no_week():
    """Match URL without /wN suffix returns None."""
    soup = _soup("https://www.vlr.gg/459521/some-match")
    assert Scraper.parse_week_number(soup) is None


def test_parse_week_number_no_canonical():
    """Page with no canonical link returns None."""
    soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
    assert Scraper.parse_week_number(soup) is None


def test_parse_week_number_w_in_slug_not_suffix():
    """Week pattern must be at the end of the URL path."""
    soup = _soup("https://www.vlr.gg/459522/w1-group-stage-match")
    assert Scraper.parse_week_number(soup) is None
