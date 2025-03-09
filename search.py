from app import ix
from whoosh.qparser import MultifieldParser
from whoosh.query import DateRange
from datetime import datetime, date

def search_emails(query_string, start_date=None, end_date=None):
    with ix.searcher() as searcher:
        query_parser = MultifieldParser(["subject", "content", "sender"], ix.schema)
        query = query_parser.parse(query_string)

        # Add date range if specified
        if start_date or end_date:
            # Convert datetime.date to datetime if needed
            if start_date and isinstance(start_date, date):
                start_date = datetime.combine(start_date, datetime.min.time())
            if end_date and isinstance(end_date, date):
                end_date = datetime.combine(end_date, datetime.max.time())

            date_range = DateRange("date", start_date, end_date)
            query = query & date_range

        results = searcher.search(query, limit=50)
        return [dict(r) for r in results]