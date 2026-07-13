from datetime import datetime, timezone

from abundroid.adapters.rss import MAX_SUMMARY_LENGTH, parse_items
from abundroid.models import Source


SOURCE = Source(
    organization='Test Publisher',
    name='Newsroom',
    url='https://example.com/feed.xml',
    format='rss',
    default_kind='article',
)


RSS = '''
<rss version='2.0' xmlns:dc='http://purl.org/dc/elements/1.1/'>
  <channel>
    <title>Publisher News</title>
    <item>
      <guid isPermaLink='false'>post-42</guid>
      <title>New homes approved</title>
      <link>https://example.com/posts/42?utm_source=feed</link>
      <dc:creator>Sam Writer</dc:creator>
      <pubDate>Thu, 09 Jul 2026 19:30:00 GMT</pubDate>
      <description><![CDATA[
        <p>One hundred <strong>new homes</strong> were approved.</p>
        <script>do not include me</script>
      ]]></description>
    </item>
    <item>
      <guid isPermaLink='false'>guid-only</guid>
      <title>Update without a link</title>
    </item>
    <item>
      <guid isPermaLink='false'>untitled</guid>
      <description>No title means this is not reviewable.</description>
    </item>
  </channel>
</rss>
'''


ATOM = '''
<feed xmlns='http://www.w3.org/2005/Atom'>
  <title>Publisher Updates</title>
  <entry>
    <id>tag:example.com,2026:update-7</id>
    <title>Program update</title>
    <updated>2026-07-09T12:15:00-07:00</updated>
    <link rel='alternate' href='https://example.com/updates/7'/>
    <link rel='canonical' href='https://example.com/canonical/7'/>
    <author><name>Alex Author</name></author>
    <summary type='html'>&lt;p&gt;A concise &lt;em&gt;update&lt;/em&gt;.&lt;/p&gt;</summary>
  </entry>
</feed>
'''


def test_parse_items_captures_rss_publication_metadata():
    items = parse_items(RSS, SOURCE)

    assert len(items) == 2
    first = items[0]
    assert first.title == 'New homes approved'
    assert first.publisher == 'Test Publisher'
    assert first.kind == 'article'
    assert first.source_item_id == 'post-42'
    assert first.canonical_url == 'https://example.com/posts/42?utm_source=feed'
    assert first.source_url == SOURCE.url
    assert first.author == 'Sam Writer'
    assert first.published_at == datetime(2026, 7, 9, 19, 30, tzinfo=timezone.utc)
    assert first.summary == 'One hundred new homes were approved.'
    assert first.uid == ''
    assert first.source_hash == ''


def test_parse_items_keeps_titled_guid_only_entries():
    item = parse_items(RSS, SOURCE)[1]

    assert item.source_item_id == 'guid-only'
    assert item.canonical_url == ''
    assert item.uid == ''


def test_parse_items_supports_atom_and_prefers_canonical_links():
    item = parse_items(ATOM, SOURCE)[0]

    assert item.source_item_id == 'tag:example.com,2026:update-7'
    assert item.canonical_url == 'https://example.com/canonical/7'
    assert item.author == 'Alex Author'
    assert item.published_at == datetime(2026, 7, 9, 19, 15, tzinfo=timezone.utc)
    assert item.summary == 'A concise update.'


def test_parse_items_bounds_plain_text_summaries():
    long_summary = 'x' * (MAX_SUMMARY_LENGTH + 100)
    feed = f'''<rss version='2.0'><channel><title>Feed</title><item>
      <guid>long</guid><title>Long summary</title>
      <description>{long_summary}</description>
    </item></channel></rss>'''

    summary = parse_items(feed, SOURCE)[0].summary

    assert len(summary) == MAX_SUMMARY_LENGTH
    assert summary == 'x' * MAX_SUMMARY_LENGTH
