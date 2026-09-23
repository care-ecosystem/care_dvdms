from django.core.cache import cache
from pydantic import BaseModel

from care_dvdms.api.services.constants import DVDMS_DRUGS_CACHE_KEY
from care_dvdms.api.services.dvdms_master_data_services import fetch_drugs
from care_dvdms.settings import plugin_settings as settings


class DVDMSDrugDetails(BaseModel):
    """Mirrors DVDMSDrug's fields, so it can be applied via model_dump()."""

    drug_id: str
    name: str
    brand_id: str
    group_id: str
    sub_group_id: str
    unit_id: str
    drug_category: str


def get_drug_details(institute, drug_id) -> DVDMSDrugDetails | None:
    drugs = cache.get(DVDMS_DRUGS_CACHE_KEY)
    if drugs is None:
        drugs = fetch_drugs()
        cache.set(DVDMS_DRUGS_CACHE_KEY, drugs, settings.DVDMS_LOOKUP_CACHE_TTL)

    for drug in drugs:
        if (
            str(drug.get("hstnum_item_id")) == str(drug_id)
            and str(drug.get("gnum_hospital_code")) == institute.eaushadhi_institute_id
            and str(drug.get("gnum_seatid")) == institute.eaushadhi_user_ref_id
        ):
            item_id = str(drug["hstnum_item_id"])
            return DVDMSDrugDetails(
                drug_id=item_id,
                name=drug.get("hststr_item_name", ""),
                brand_id=item_id,
                group_id=str(drug.get("hstnum_group_id", "")),
                sub_group_id=str(drug.get("hstnum_subgroup_id", "")),
                unit_id=str(drug.get("gnum_inventory_unitid", "")),
                drug_category=str(drug.get("sstnum_item_cat_no", "")),
            )
    return None
