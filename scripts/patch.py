
text = """
    async def _scrape_programs_api(self, max_programs: int = 100, study_level: str = None) -> list:
        \"\"\"Scrape primary program list via API.\"\"\"
        import json
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Discovering up to {max_programs} programs via API...")
        results = []
        page = 0
        while len(results) < max_programs:
            await self._rate_limit_delay(fast=True)
            url = f"{self.base_url}/pd/endpoint?page={page}&items_per_page=50"
            if study_level:
                url += f"&level={study_level}"
            try:
                if not self._http_client: return results
                resp = await self._http_client.get(
                    url,
                    headers=self._build_headers(referer=f"{self.base_url}/programs"),
                    timeout=self.rate_limiting["timeout_seconds"]
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    results.append({
                        "title": item.get("title"),
                        "university": item.get("univ", {}).get("title"),
                        "url": f"{self.base_url}{item.get('url')}" if item.get("url") else None
                    })
                page += 1
            except Exception as e:
                logger.error(f"API fetch error: {e}")
                break
        return results[:max_programs]

    async def scrape_programs_with_details(self, max_programs: int = 100, study_level: str = None, on_progress = None) -> list:
        \"\"\"Perform 2-stage scrape: Quick API discovery then deep HTTP extraction.\"\"\"
        import traceback
        import asyncio
        from bs4 import BeautifulSoup
        import logging
        logger = logging.getLogger(__name__)

        discovery = await self._scrape_programs_api(max_programs, study_level)

        logger.info(f"Deep scraping {len(discovery)} programs...")
        semaphore = asyncio.Semaphore(20)

        async def enrich_one(program: dict) -> dict:
            url = program.get("url") or program.get("program_url")
            if not url:
                return program

            async with semaphore:
                try:
                    await self._rate_limit_delay(fast=True)
                    html_headers = self._build_headers(referer=f"{self.base_url}/programs")
                    html_headers.pop("X-Requested-With", None)
                    html_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

                    response = await self._http_client.get(
                        url, headers=html_headers, timeout=self.rate_limiting.get("timeout_seconds", 30), follow_redirects=True
                    )
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, "html.parser")
                    detail = self._extract_page_fields(soup, url)

                    if on_progress:
                        on_progress(1, len(discovery))

                    return {**program, **{k: v for k, v in detail.items() if v is not None and k != "error"}}
                except Exception as e:
                    logger.error(f"Deep scrape failed for {url}: {e}\\n{traceback.format_exc()}")
                    return program

        enriched = await asyncio.gather(*[enrich_one(p) for p in discovery], return_exceptions=True)
        final_results = []
        for r in enriched:
            if isinstance(r, dict):
                final_results.append(r)
        return final_results

    def _extract_page_fields(self, soup, url: str) -> dict:
        \"\"\"Parse structured data from a deep program page.\"\"\"
        import re
        detail = {
            "program_url": url,
            "duration": None,
            "tuition_fee_summary": None,
            "degree_type": None,
            "study_level": None,
            "cambridge_cae_score": None,
            "pte_score": None,
            "ielts_score": None,
            "toefl_score": None,
            "sat_score": None,
            "gmat_score": None,
            "gre_score": None,
            "fee_domestic": None,
            "fee_international": None,
            "fee_currency": None,
        }

        title_elem = soup.select_one("h1")
        if title_elem:
            detail["program_name"] = title_elem.get_text(strip=True)

        for box in soup.select(".badge-description, .program-quick-details-v2 .detail-box, .program-quick-details .detail-box"):
            label_elem = box.select_one("label, .label, span.title")
            val_elem = box.select_one(".value, .detail-value, span.value")
            if label_elem and val_elem:
                label = label_elem.get_text().lower()
                value = val_elem.get_text(strip=True)
                if "duration" in label: detail["duration"] = value
                elif "tuition" in label or "fee" in label: detail["tuition_fee_summary"] = value
                elif "degree" in label: detail["degree_type"] = value
                elif "level" in label: detail["study_level"] = value

        for fee_div in soup.select(".fee-block, .tuition-fees, .tuition-card, div"):
            text = fee_div.get_text(strip=True).lower()

            if "domestic" in text and not detail["fee_domestic"]:
                m = re.search(r"domestic.*?(?:£|\\$|€|sgd|usd|gbp)\\s*([0-9,]+)", text)
                if m: detail["fee_domestic"] = m.group(1)
            if "international" in text and not detail["fee_international"]:
                m = re.search(r"international.*?(?:£|\\$|€|sgd|usd|gbp)\\s*([0-9,]+)", text)
                if m: detail["fee_international"] = m.group(1)

        for req in soup.select("p, li, td"):
            text = req.get_text(strip=True).lower()
            if "ielts" in text and not detail["ielts_score"]:
                m = re.search(r"ielts\\s*[:\\-]?\\s*([0-9\\.]+)", text)
                if m: detail["ielts_score"] = m.group(1) + "+"
            if "toefl" in text and not detail["toefl_score"]:
                m = re.search(r"toefl\\s*[:\\-]?\\s*([0-9]{2,3})", text)
                if m: detail["toefl_score"] = m.group(1) + "+"
            if "pte" in text and not detail["pte_score"]:
                m = re.search(r"pte\\s*[:\\-]?\\s*([0-9]{2,3})", text)
                if m: detail["pte_score"] = m.group(1) + "+"

        return detail
"""

with open("src/scrapers/topuniversities_scraper.py", "a", encoding="utf-8") as f:
    f.write(text)

print("Patch applied.")
