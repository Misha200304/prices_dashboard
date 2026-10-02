from backfill_fertilizer_history import parse_report_html


def test_parse_report_html_extracts_price_and_region_count():
    html = """
    <html>
      <body>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Formula</th>
              <th>Avg Price/Ton</th>
              <th>Change</th>
              <th>% Change</th>
              <th>Regions</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>DAP</td>
              <td>18-46-0</td>
              <td>$945.56</td>
              <td>-$16.27</td>
              <td>-1.7%</td>
              <td>2</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    result = parse_report_html(
        html,
        "https://fertilizerprice.com/news/fertilizer-prices-week-2026-10-02",
    )

    assert len(result) == 1
    assert result.iloc[0]["Date"] == "2026-10-02"
    assert result.iloc[0]["Commodity"] == "DAP"
    assert result.iloc[0]["Price"] == 945.56
    assert result.iloc[0]["Regions_Reported"] == 2
    assert result.iloc[0]["Series"] == "reported_national"
