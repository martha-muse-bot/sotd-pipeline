from datetime import datetime, timezone
from typing import Any, Dict, List

from .soap_scent_filter import counts_as_distinct_soap_scent, is_mashup_soap


def calculate_shaves(records: List[Dict[str, Any]]) -> int:
    """Calculate total number of shaves from records."""
    return len(records)


def calculate_unique_users(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique users from records."""
    if not records:
        return 0

    # Use a more defensive approach with pandas
    authors = set()
    for record in records:
        author = record.get("author")
        if author and author is not None:
            author = str(author).strip()
            if author:
                authors.add(author)
    return len(authors)


def calculate_avg_shaves_per_user(records: List[Dict[str, Any]]) -> float:
    """Calculate average shaves per user."""
    total_shaves = calculate_shaves(records)
    unique_users = calculate_unique_users(records)
    if unique_users == 0:
        return 0.0
    return round(total_shaves / unique_users, 2)


def calculate_median_shaves_per_user(records: List[Dict[str, Any]]) -> float:
    """Calculate median shaves per user."""
    if not records:
        return 0.0

    # Count shaves per user using a more defensive approach
    user_shaves = {}
    for record in records:
        author = record.get("author")
        if author and author is not None:
            author = str(author).strip()
            if author:  # Skip None, empty strings, and whitespace-only strings
                user_shaves[author] = user_shaves.get(author, 0) + 1

    if not user_shaves:
        return 0.0

    # Calculate median
    shave_counts = list(user_shaves.values())
    shave_counts.sort()
    n = len(shave_counts)

    if n % 2 == 0:
        # Even number of users, average of two middle values
        median = (shave_counts[n // 2 - 1] + shave_counts[n // 2]) / 2
    else:
        # Odd number of users, middle value
        median = shave_counts[n // 2]

    return round(median, 2)


def calculate_unique_soaps(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique soaps from records.

    Excludes non-countable scents and mashups (soap.enriched.is_mashup).
    """
    if not records:
        return 0

    # Extract soap data and filter for valid entries
    soap_data = []
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            if not counts_as_distinct_soap_scent(soap):
                continue

            matched = soap.get("matched", {})
            if matched and isinstance(matched, dict):
                brand = matched.get("brand")
                scent = matched.get("scent")

                if brand and isinstance(brand, str) and scent and isinstance(scent, str):
                    brand = brand.strip()
                    scent = scent.strip()
                    if brand and scent:
                        soap_data.append(f"{brand} - {scent}".lower())

    return len(set(soap_data))


def calculate_unique_brands(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique soap brands from records."""
    if not records:
        return 0

    # Extract soap brands and filter for valid entries
    brands = []
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            matched = soap.get("matched", {})
            if matched and isinstance(matched, dict):
                brand = matched.get("brand")
                if brand and isinstance(brand, str):
                    brand = brand.strip()
                    if brand:
                        brands.append(brand)

    return len(set(brands))


def calculate_total_samples(records: List[Dict[str, Any]]) -> int:
    """Calculate total number of sample shaves from records."""
    if not records:
        return 0

    # Count records with sample_type
    sample_count = 0
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            enriched = soap.get("enriched", {})
            if enriched and enriched.get("sample_type"):
                if is_mashup_soap(soap):
                    continue
                sample_count += 1

    return sample_count


def calculate_sample_users(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique users who used samples."""
    if not records:
        return 0

    # Extract users who used samples
    sample_users = []
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            enriched = soap.get("enriched", {})
            if enriched and enriched.get("sample_type"):
                if is_mashup_soap(soap):
                    continue
                author = record.get("author")
                if author and isinstance(author, str) and author.strip():
                    sample_users.append(author.strip())

    return len(set(sample_users))


def calculate_total_mashup_shaves(records: List[Dict[str, Any]]) -> int:
    """Calculate total number of shaves that used a mashup (soap.enriched.is_mashup)."""
    if not records:
        return 0

    count = 0
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            enriched = soap.get("enriched", {})
            if enriched and enriched.get("is_mashup") is True:
                count += 1
    return count


def calculate_mashup_users(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique users who used a mashup (soap.enriched.is_mashup)."""
    if not records:
        return 0

    mashup_users = []
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            enriched = soap.get("enriched", {})
            if enriched and enriched.get("is_mashup") is True:
                author = record.get("author")
                if author and isinstance(author, str) and author.strip():
                    mashup_users.append(author.strip())

    return len(set(mashup_users))


def calculate_sample_brands(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique brands sampled."""
    if not records:
        return 0

    # Extract brands from samples
    sample_brands = []
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            enriched = soap.get("enriched", {})
            matched = soap.get("matched", {})

            # Skip if no sample data OR if sample_type is None/empty (not actually used)
            if not enriched or "sample_type" not in enriched:
                continue

            # Check if sample_type actually has a value (not None or empty string)
            sample_type = enriched.get("sample_type")
            if not sample_type:  # This catches None, "", and other falsy values
                continue

            if is_mashup_soap(soap):
                continue

            if matched and isinstance(matched, dict):
                brand = matched.get("brand")
                if brand and isinstance(brand, str):
                    brand = brand.strip()
                    if brand:
                        sample_brands.append(brand)

    return len(set(sample_brands))


def calculate_unique_sample_soaps(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique sample soaps from records."""
    if not records:
        return 0

    # Extract sample soaps and filter for valid entries
    sample_soaps = []
    for record in records:
        soap = record.get("soap")
        if soap is not None and isinstance(soap, dict):
            enriched = soap.get("enriched", {})
            matched = soap.get("matched", {})

            # Skip if no sample data OR if sample_type is None/empty (not actually used)
            if not enriched or "sample_type" not in enriched:
                continue

            # Check if sample_type actually has a value (not None or empty string)
            sample_type = enriched.get("sample_type")
            if not sample_type:  # This catches None, "", and other falsy values
                continue

            if is_mashup_soap(soap):
                continue

            # Skip if no matched soap data
            if not matched or not matched.get("brand") or not matched.get("scent"):
                continue

            brand = matched.get("brand")
            scent = matched.get("scent")

            if brand and isinstance(brand, str) and scent and isinstance(scent, str):
                brand = brand.strip()
                scent = scent.strip()
                if brand and scent:
                    soap_name = f"{brand} - {scent}"
                    sample_soaps.append(soap_name)

    return len(set(sample_soaps))


def calculate_unique_razors(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique razors from records."""
    if not records:
        return 0

    # Extract razor data and filter for valid entries
    razors = []
    for record in records:
        razor = record.get("razor")
        if razor is not None and isinstance(razor, dict):
            matched = razor.get("matched", {})
            if matched and isinstance(matched, dict):
                brand = matched.get("brand")
                model = matched.get("model")
                if brand and isinstance(brand, str) and model and isinstance(model, str):
                    brand = brand.strip()
                    model = model.strip()
                    if brand and model:
                        razors.append(f"{brand} {model}")

    return len(set(razors))


def calculate_unique_blades(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique blades from records."""
    if not records:
        return 0

    # Extract blade data and filter for valid entries
    blades = []
    for record in records:
        blade = record.get("blade")
        if blade is not None and isinstance(blade, dict):
            matched = blade.get("matched", {})
            if matched and isinstance(matched, dict):
                brand = matched.get("brand")
                model = matched.get("model")
                if brand and isinstance(brand, str) and model and isinstance(model, str):
                    brand = brand.strip()
                    model = model.strip()
                    if brand and model:
                        blades.append(f"{brand} {model}")

    return len(set(blades))


def calculate_unique_brushes(records: List[Dict[str, Any]]) -> int:
    """Calculate number of unique brushes from records."""
    if not records:
        return 0

    # Extract brush data and filter for valid entries
    brushes = []
    for record in records:
        brush = record.get("brush")
        if brush is not None and isinstance(brush, dict):
            matched = brush.get("matched", {})
            if matched and isinstance(matched, dict):
                brand = matched.get("brand")
                model = matched.get("model")
                if brand and isinstance(brand, str) and model and isinstance(model, str):
                    brand = brand.strip()
                    model = model.strip()
                    if brand and model:
                        brushes.append(f"{brand} {model}")

    return len(set(brushes))


def add_rank_field(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add rank field (1-based rank) to list of items."""
    for i, item in enumerate(items, 1):
        item["rank"] = i
    return items


def calculate_metadata(records: List[Dict[str, Any]], month: str) -> Dict[str, Any]:
    """Generate metadata for aggregated data.

    Args:
        records: List of enriched comment records
        month: Month being processed (YYYY-MM format)

    Returns:
        Dictionary containing metadata with month, total_shaves, unique_shavers,
        avg_shaves_per_user, median_shaves_per_user, unique_soaps, unique_brands,
        total_samples, sample_users, sample_brands, unique_sample_soaps,
        unique_razors, unique_blades, and unique_brushes
    """
    total_shaves = calculate_shaves(records)

    unique_shavers = calculate_unique_users(records)

    avg_shaves_per_user = calculate_avg_shaves_per_user(records)

    median_shaves_per_user = calculate_median_shaves_per_user(records)

    unique_soaps = calculate_unique_soaps(records)

    unique_brands = calculate_unique_brands(records)

    total_samples = calculate_total_samples(records)

    sample_users = calculate_sample_users(records)

    sample_brands = calculate_sample_brands(records)

    unique_sample_soaps = calculate_unique_sample_soaps(records)

    total_mashup_shaves = calculate_total_mashup_shaves(records)
    mashup_users = calculate_mashup_users(records)
    mashup_percentage = (
        round((total_mashup_shaves / total_shaves) * 100, 1) if total_shaves > 0 else 0.0
    )

    unique_razors = calculate_unique_razors(records)

    unique_blades = calculate_unique_blades(records)

    unique_brushes = calculate_unique_brushes(records)

    return {
        "month": month,
        "aggregated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "total_shaves": total_shaves,
        "unique_shavers": unique_shavers,
        "avg_shaves_per_user": avg_shaves_per_user,
        "median_shaves_per_user": median_shaves_per_user,
        "unique_soaps": unique_soaps,
        "unique_brands": unique_brands,
        "total_samples": total_samples,
        "sample_users": sample_users,
        "sample_brands": sample_brands,
        "unique_sample_soaps": unique_sample_soaps,
        "total_mashup_shaves": total_mashup_shaves,
        "mashup_users": mashup_users,
        "mashup_percentage": mashup_percentage,
        "unique_razors": unique_razors,
        "unique_blades": unique_blades,
        "unique_brushes": unique_brushes,
    }
