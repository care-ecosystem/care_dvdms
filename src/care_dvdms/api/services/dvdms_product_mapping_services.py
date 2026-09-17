import logging

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from care_dvdms.models.dvdms_drug import DVDMSDrug
from care_dvdms.models.dvdms_product_mapping import DVDMSProductMapping, DVDMSProductMappingType

logger = logging.getLogger(__name__)


def _find_product_mapping(institute, product_knowledge_id, drug_spec):
    """
    The institute's mapping covering this drug group, sub group and name for the given
    product, whichever way it was established. Where more than one qualifies, the most
    used and then most recently touched one wins.
    """
    return (
        DVDMSProductMapping.objects.filter(
            institute=institute,
            product_knowledge_id=product_knowledge_id,
            drug__group_id=drug_spec.group_id,
            drug__sub_group_id=drug_spec.sub_group_id,
            drug__name=drug_spec.name,
            deleted=False,
        )
        .order_by("-usage_count", "-modified_date")
        .first()
    )


def sync_product_mapping(institute, product_knowledge_id, drug_spec, user):
    """
    Keep the institute's drug to product mappings in step with the drugs being ordered.

    A mapping already covering this drug group, sub group and name for the product counts
    one more use. An unseen combination is recorded as a manual mapping so the next order
    finds it. Returns the mapping, or None when one could not be recorded.
    """
    existing = _find_product_mapping(institute, product_knowledge_id, drug_spec)
    if existing:
        existing.usage_count = F("usage_count") + 1
        existing.last_used_date = timezone.now()
        existing.updated_by = user
        existing.save(
            update_fields=["usage_count", "last_used_date", "updated_by", "modified_date"]
        )
        return existing

    try:
        with transaction.atomic():
            mapping_drug = DVDMSDrug.objects.create(
                drug_id=drug_spec.id,
                name=drug_spec.name,
                brand_id=drug_spec.brand_id,
                group_id=drug_spec.group_id,
                sub_group_id=drug_spec.sub_group_id,
                unit_id=drug_spec.unit_id,
                drug_category=drug_spec.drug_category,
                created_by=user,
                updated_by=user,
            )
            return DVDMSProductMapping.objects.create(
                institute=institute,
                drug=mapping_drug,
                eaushadhi_drug_id=drug_spec.id,
                product_knowledge_id=product_knowledge_id,
                mapping_type=DVDMSProductMappingType.manual_mapping,
                usage_count=1,
                last_used_date=timezone.now(),
                created_by=user,
                updated_by=user,
            )
    except IntegrityError:
        logger.warning(
            "Skipped auto product mapping: drug %s is already mapped to another product "
            "for institute %s",
            drug_spec.id,
            institute.external_id,
        )
        return None
