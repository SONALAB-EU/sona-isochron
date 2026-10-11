# Step 2 on test: prompt v1 without and with the repair loop

- Date: 2026-10-11 12:48 UTC
- Git commit (report): d98b12e966443e3121ca4ec5064ffa3608ef2604 (with uncommitted changes to tracked files); runs: `hpc_8b_step2_de_test` (68492f2 (synced copy, recorded by hpc/sync.sh))
- Model: apertus-v1.5-8b-bf16, quantisation BF16, endpoint http://127.0.0.1:38657/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}; round seeds: item seed + 1000 × round (round 0 uses the item seed)
- Prompt `shorten_syllables_v1` (fe4fbfdd800d); repair `revise_v1` (ab0593b9716e), at most 2 rounds
- Loop checks: eSpeak NG text-to-speech: 1.52.0, NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label, language check py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9
- Judge (evaluation only): qwen3-14b-bf16 (BF16), endpoint http://127.0.0.1:53663/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99, temperature 0, seed 0, mode perfact_v3
- Items: de test: 347 sentences × levels [90, 80, 70, 60] × seeds [0, 1, 2]; TTS: none
- 95 % intervals: bootstrap over sentences (each carries its levels and seeds), 10000 resamples, seed 0.

<!-- Hand-written summary section of results/step2_test.md, inserted by `python -m isochron.step2_report RUN_DIR... --notes results/step2_test_notes.md`. Date, commits, model, endpoint, TTS, seeds and n are in that report's header. -->

## Summary

These are the final numbers for FLEURS German test: 347 sentences × levels 90, 80, 70 and 60 % × seeds 0, 1
and 2, so 4,164 outputs per condition.
- Apertus 1.5 8B ran in BF16 (the official weights) on vLLM, on one H100. The judge, Qwen3-14B BF16, was
  used for evaluation only.
- Both conditions come from the same run: "without the loop" is the closest round-0 candidate.
- **French: pending.** Job 2636593 has waited for a free H100 since 12:42 UTC. This report will be
  generated again with both languages.

**German, pooled over the four levels:**
- **The repair loop helps.**
  - Fit rises from 34.9 % to 64.7 % (+29.8 points [27.2, 32.4], paired).
  - Fit & complete rises from 14.2 % to 38.4 % (+24.3 points [22.2, 26.3]).
  - Fact recall rises from 59.9 % to 78.0 % (+18.0 points [16.0, 20.1]).
- **The gain shrinks as the target tightens.** Fit & complete rises by:

  | Level | Gain in points |
  |------:|----------------|
  | 90 % | +56.7 [52.7, 60.5] |
  | 80 % | +28.5 [24.9, 32.2] |
  | 70 % | +10.2 [7.7, 12.8] |
  | 60 % | +1.6 [−0.6, +3.8], which cannot be told from zero |

- **At 60 % the loop does not improve fit** (−1.5 points [−5.6, +2.5]).
  - When no candidate both fits and keeps the meaning, the loop keeps the meaning. NLI kept rises from
    52 % to 96 %.
  - So the outputs run long: achieved ÷ target is 1.08.
- **Without the loop, Apertus over-shortens:** achieved ÷ target is 0.83 overall, and 0.71 at level 90.
  With the loop it is 1.05.
- **With the loop, misses run long, and some outputs are the input unchanged.** This is analysis of the
  same outputs, not a new metric.
  - Misses that are too long outnumber those too short at every level. At 60 %, 321 are too long and 145
    too short, of 1,041.
  - The final output is the input unchanged in this share of items:

    | Level | Unchanged input |
    |------:|----------------:|
    | 90 % | 9.4 % |
    | 80 % | 4.7 % |
    | 70 % | 3.0 % |
    | 60 % | 2.0 % |

  - At 90 %, an unchanged input is about 1.11 × the target, just outside the ±10 % band.
- **Clean runs.**
  - No output is in the wrong language, in either condition.
  - Round 0 left 28 items without a usable answer. With the loop there are none, after 33 retries.
  - None of the 8,328 judge verdicts is invalid.
- **Added facts.** The added-fact rate is about 0 % in both conditions. The judge caught 16 of 20
  inserted facts on the controls, so this means few added facts, not none.
- **Cost.** With 16 items in flight on one H100, an output takes 10.5 s with the loop (every round and
  check) and 0.7 s for round 0. The loop adds 1.21 rounds on average.

**Caveats.**
- Fact recall and fit & complete are upper bounds. The judge misses half of the lost qualifiers on the
  hard controls (7 of 14), and the NLI misses most of them (3 of 14).
- Syllables stand in for spoken time; no speech was synthesised.
- Outputs are not checked for grammar.

Fit, fact recall, added-fact rate and fit & complete are in %. Fit & complete = the output fits and the judge
keeps every fact and finds nothing added. NLI kept is the loop's own check, reported as a screen. A missing
or wrong-language output counts as a failure. Without the loop = the closest round-0 candidate of the same run.

## DE (test)

### DE: all levels (90 %, 80 %, 70 %, 60 %)

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 4164 | 34.9 [32.5, 37.3] | 59.9 [57.0, 62.8] | 0.1 [0.0, 0.2] | 14.2 [12.4, 16.1] | 55 % | 0.83 | 0.00 | 0 | 0.7 | 28 | 0 | 0 |
| v1 | with | 4164 | 64.7 [62.1, 67.2] | 78.0 [75.9, 80.0] | 0.0 [0.0, 0.1] | 38.4 [35.7, 41.2] | 98 % | 1.05 | 1.21 | 33 | 10.5 | 0 | 0 | 0 |

### DE: effect of the repair loop (with − without, percentage points)

| Levels | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete |
|--------|-----------|-------------|-----------------|----------------|
| all | +29.8 [+27.2, +32.4] | +18.0 [+16.0, +20.1] | -0.0 [-0.1, +0.0] | +24.3 [+22.2, +26.3] |
| 90 % | +69.8 [+66.1, +73.4] | +28.6 [+25.8, +31.4] | +0.0 [+0.0, +0.0] | +56.7 [+52.7, +60.5] |
| 80 % | +38.1 [+34.0, +42.3] | +21.1 [+18.2, +23.9] | -0.1 [-0.3, +0.0] | +28.5 [+24.9, +32.2] |
| 70 % | +12.9 [+8.7, +17.0] | +13.5 [+10.9, +16.0] | +0.0 [+0.0, +0.0] | +10.2 [+7.7, +12.8] |
| 60 % | -1.5 [-5.6, +2.5] | +9.0 [+6.6, +11.5] | -0.1 [-0.3, +0.0] | +1.6 [-0.6, +3.8] |

Higher is better, except for the added-fact rate. Sentences that lack a judge verdict in one condition are left out of that column's difference.

### DE: level 90 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 11.7 [9.0, 14.5] | 62.6 [59.5, 65.7] | 0.0 [0.0, 0.0] | 8.5 [6.3, 10.8] | 58 % | 0.71 | 0.00 | 0 | 0.7 | 6 | 0 | 0 |
| v1 | with | 1041 | 81.6 [78.4, 84.4] | 91.2 [89.5, 92.8] | 0.0 [0.0, 0.0] | 65.1 [61.4, 68.8] | 98 % | 1.02 | 1.16 | 8 | 10.5 | 0 | 0 | 0 |

### DE: level 80 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 26.7 [23.2, 30.4] | 61.2 [58.0, 64.4] | 0.2 [0.0, 0.5] | 13.0 [10.5, 15.7] | 56 % | 0.79 | 0.00 | 0 | 0.7 | 6 | 0 | 0 |
| v1 | with | 1041 | 64.8 [61.2, 68.4] | 82.3 [79.8, 84.7] | 0.1 [0.0, 0.3] | 41.5 [37.7, 45.3] | 98 % | 1.03 | 1.26 | 6 | 10.8 | 0 | 0 | 0 |

### DE: level 70 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 44.5 [40.3, 48.6] | 59.1 [55.9, 62.3] | 0.0 [0.0, 0.0] | 16.1 [13.4, 19.2] | 55 % | 0.87 | 0.00 | 0 | 0.7 | 7 | 0 | 0 |
| v1 | with | 1041 | 57.3 [53.5, 61.2] | 72.6 [69.6, 75.5] | 0.0 [0.0, 0.0] | 26.3 [22.9, 30.0] | 98 % | 1.04 | 1.22 | 8 | 10.4 | 0 | 0 | 0 |

### DE: level 60 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 56.8 [52.7, 60.6] | 56.7 [53.6, 59.9] | 0.1 [0.0, 0.3] | 19.1 [15.9, 22.4] | 52 % | 0.96 | 0.00 | 0 | 0.7 | 9 | 0 | 0 |
| v1 | with | 1041 | 55.2 [51.3, 59.1] | 65.7 [62.7, 68.7] | 0.0 [0.0, 0.0] | 20.7 [17.4, 24.1] | 96 % | 1.08 | 1.22 | 11 | 10.5 | 0 | 0 | 0 |

## Judge validation

`results/judge_validation_hard_v3_qwen3-14b_hpc_8b.md`: Mean accuracy over the 6 control types: 84 %

| Control | Expected (judge) | DE | All | NLI, all |
|---------|------------------|---:|---:|---:|
| identity | complete: recall 1, nothing added | 100 % (60/60) | 100 % (60/60) | 92 % (55/60) |
| same_meaning | complete: recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 90 % (18/20) |
| modal_changed | not complete | 77 % (10/13) | 77 % (10/13) | 77 % (10/13) |
| number_changed | not complete | 100 % (13/13) | 100 % (13/13) | 92 % (12/13) |
| qualifier_changed | not complete | 50 % (7/14) | 50 % (7/14) | 21 % (3/14) |
| fact_inserted | something added | 80 % (16/20) | 80 % (16/20) | 100 % (20/20) |

`results/judge_validation_nli_v3_qwen3-14b_hpc_8b.md`: Mean accuracy over the 5 control types: 99 %

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 95 % (38/40) |
| paraphrase | recall 1, nothing added | 100 % (20/20) | 95 % (19/20) | 98 % (39/40) | 95 % (38/40) |
| clause_deleted | recall < 1, nothing added | 100 % (20/20) | 95 % (19/20) | 98 % (39/40) | 82 % (33/40) |
| clause_inserted | recall 1, something added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 90 % (36/40) |
| negation | recall < 1 | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 100 % (40/40) |

## Run configurations

### `hpc_8b_step2_de_test`

<details><summary>config.json</summary>

```json
{
  "date": "2026-10-11T11:46:00+00:00",
  "git_commit": "68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh)",
  "phase": 2,
  "kind": "loop run",
  "variant": "v1",
  "lang": "de",
  "split": "test",
  "levels": [
    90,
    80,
    70,
    60
  ],
  "seeds": [
    0,
    1,
    2
  ],
  "repair": true,
  "max_revisions": 2,
  "round_seed": "item seed + 1000 × round (round 0 uses the item seed)",
  "mock": false,
  "model": "apertus-v1.5-8b-bf16",
  "quantisation": "BF16",
  "endpoint": "http://127.0.0.1:38657/v1",
  "backend": {
    "type": "vLLM",
    "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99",
    "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/swiss-ai/Apertus-v1.5-8B",
    "max_model_len": 8192
  },
  "generation": {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 0,
    "min_p": 0.0,
    "max_tokens": 1024,
    "chat_template_kwargs": {
      "enable_thinking": false
    }
  },
  "prompt": {
    "name": "shorten_syllables_v1",
    "sha256": "fe4fbfdd800d69b613fd49ba747507aa44a9a868556ceca15421d33edd661a5c"
  },
  "revise_prompt": {
    "name": "revise_v1",
    "sha256": "ab0593b9716e97e17444e36c243206f65a62f5d46d3421423cfdeda2f55c5c57"
  },
  "length_counter": {
    "syllables": "eSpeak NG text-to-speech: 1.52.0",
    "counter": "espeak"
  },
  "nli": "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label",
  "nli_model": "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb38ab63efdd7f280f8c144ea8b13f978ce",
  "language_check": "py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9",
  "loop_uses": "language identifier, syllable counter and NLI only; never the final judge",
  "data": {
    "file": "data/fleurs_de_test.jsonl",
    "sha256": "560d7e8ca492ddc4b8df1c1e72bb8243e48e8275c81ccbb91515bb70f4bcbbca"
  },
  "items": {
    "selection": "all sentences in file order",
    "n": 347,
    "ids": [
      "1660",
      "1661",
      "1662",
      "1663",
      "1664",
      "1665",
      "1666",
      "1667",
      "1668",
      "1669",
      "1670",
      "1671",
      "1672",
      "1673",
      "1674",
      "1675",
      "1676",
      "1677",
      "1678",
      "1679",
      "1680",
      "1682",
      "1683",
      "1684",
      "1685",
      "1686",
      "1687",
      "1688",
      "1689",
      "1690",
      "1691",
      "1692",
      "1693",
      "1694",
      "1695",
      "1696",
      "1697",
      "1698",
      "1699",
      "1700",
      "1701",
      "1702",
      "1703",
      "1704",
      "1705",
      "1706",
      "1707",
      "1708",
      "1709",
      "1710",
      "1711",
      "1712",
      "1713",
      "1714",
      "1715",
      "1716",
      "1717",
      "1718",
      "1719",
      "1720",
      "1721",
      "1722",
      "1723",
      "1724",
      "1725",
      "1726",
      "1727",
      "1728",
      "1729",
      "1730",
      "1731",
      "1732",
      "1733",
      "1734",
      "1735",
      "1736",
      "1737",
      "1738",
      "1739",
      "1740",
      "1741",
      "1742",
      "1743",
      "1744",
      "1745",
      "1746",
      "1747",
      "1748",
      "1749",
      "1750",
      "1751",
      "1752",
      "1753",
      "1754",
      "1755",
      "1756",
      "1757",
      "1758",
      "1759",
      "1760",
      "1761",
      "1762",
      "1763",
      "1764",
      "1765",
      "1766",
      "1767",
      "1768",
      "1769",
      "1770",
      "1771",
      "1772",
      "1773",
      "1774",
      "1775",
      "1776",
      "1777",
      "1778",
      "1779",
      "1780",
      "1781",
      "1782",
      "1783",
      "1784",
      "1785",
      "1786",
      "1787",
      "1788",
      "1789",
      "1790",
      "1791",
      "1792",
      "1793",
      "1794",
      "1795",
      "1796",
      "1797",
      "1798",
      "1799",
      "1800",
      "1801",
      "1802",
      "1803",
      "1804",
      "1805",
      "1806",
      "1807",
      "1808",
      "1809",
      "1810",
      "1811",
      "1812",
      "1813",
      "1814",
      "1815",
      "1816",
      "1817",
      "1818",
      "1819",
      "1820",
      "1821",
      "1822",
      "1823",
      "1824",
      "1825",
      "1826",
      "1827",
      "1828",
      "1829",
      "1830",
      "1831",
      "1832",
      "1833",
      "1834",
      "1835",
      "1836",
      "1837",
      "1838",
      "1839",
      "1840",
      "1841",
      "1843",
      "1844",
      "1845",
      "1846",
      "1847",
      "1848",
      "1849",
      "1850",
      "1851",
      "1852",
      "1853",
      "1855",
      "1856",
      "1857",
      "1858",
      "1859",
      "1860",
      "1861",
      "1862",
      "1863",
      "1864",
      "1865",
      "1866",
      "1867",
      "1868",
      "1869",
      "1870",
      "1871",
      "1872",
      "1873",
      "1874",
      "1875",
      "1876",
      "1877",
      "1878",
      "1879",
      "1880",
      "1881",
      "1882",
      "1883",
      "1884",
      "1885",
      "1886",
      "1887",
      "1888",
      "1889",
      "1890",
      "1891",
      "1892",
      "1893",
      "1894",
      "1895",
      "1896",
      "1897",
      "1898",
      "1899",
      "1900",
      "1901",
      "1902",
      "1903",
      "1904",
      "1905",
      "1906",
      "1907",
      "1908",
      "1909",
      "1910",
      "1911",
      "1912",
      "1913",
      "1914",
      "1915",
      "1916",
      "1917",
      "1918",
      "1919",
      "1920",
      "1921",
      "1922",
      "1923",
      "1924",
      "1925",
      "1926",
      "1927",
      "1928",
      "1929",
      "1930",
      "1931",
      "1932",
      "1933",
      "1934",
      "1935",
      "1936",
      "1937",
      "1938",
      "1939",
      "1940",
      "1941",
      "1942",
      "1943",
      "1944",
      "1945",
      "1946",
      "1947",
      "1948",
      "1949",
      "1950",
      "1951",
      "1952",
      "1953",
      "1954",
      "1955",
      "1956",
      "1957",
      "1958",
      "1959",
      "1960",
      "1961",
      "1962",
      "1963",
      "1964",
      "1965",
      "1966",
      "1967",
      "1968",
      "1969",
      "1970",
      "1971",
      "1972",
      "1973",
      "1974",
      "1975",
      "1976",
      "1977",
      "1978",
      "1979",
      "1980",
      "1981",
      "1982",
      "1983",
      "1984",
      "1985",
      "1986",
      "1987",
      "1988",
      "1989",
      "1990",
      "1991",
      "1992",
      "1993",
      "1994",
      "1995",
      "1996",
      "1997",
      "1998",
      "1999",
      "2000",
      "2001",
      "2002",
      "2003",
      "2004",
      "2005",
      "2006",
      "2007",
      "2008",
      "2009"
    ]
  },
  "tts": "none",
  "workers": 16,
  "sessions": [
    {
      "started": "2026-10-11T11:46:00+00:00",
      "git_commit": "68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh)",
      "workers": 16,
      "endpoint": "http://127.0.0.1:38657/v1",
      "backend": {
        "type": "vLLM",
        "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99",
        "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/swiss-ai/Apertus-v1.5-8B",
        "max_model_len": 8192
      },
      "nli": "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label"
    }
  ]
}
```

</details>

<details><summary>judge_config.json</summary>

```json
{
  "date": "2026-10-11T12:42:28+00:00",
  "git_commit": "68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh)",
  "model": "qwen3-14b-bf16",
  "endpoint": "http://127.0.0.1:53663/v1",
  "backend": {
    "type": "vLLM",
    "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99",
    "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/Qwen/Qwen3-14B",
    "max_model_len": 8192
  },
  "quantisation": "BF16",
  "generation": {
    "temperature": 0.0,
    "max_tokens": 1024,
    "chat_template_kwargs": {
      "enable_thinking": false
    }
  },
  "seed": 0,
  "mode": "perfact_v3",
  "prompts": {
    "judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1",
    "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587",
    "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"
  }
}
```

</details>

