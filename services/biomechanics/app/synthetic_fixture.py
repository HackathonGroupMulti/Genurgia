from uuid import UUID

from app.schemas.reconstruction import REQUIRED_KNEE_STRUCTURES


def synthetic_fe_manifest(
    reconstruction_id: UUID,
    laterality: str,
    coordinate_system: str,
) -> dict[str, object]:
    """Build the small CC0 topology fixture; it is not anatomical evidence."""
    structures = [
        "femur",
        "tibia",
        "femoral_cartilage",
        "medial_tibial_cartilage",
        "lateral_tibial_cartilage",
        "medial_meniscus",
        "lateral_meniscus",
    ]
    nodes = [
        {"id": 1, "position_mm": [0, 0, 4]},
        {"id": 2, "position_mm": [2, 0, 4]},
        {"id": 3, "position_mm": [0, 2, 4]},
        {"id": 4, "position_mm": [0, 0, 6]},
        {"id": 5, "position_mm": [0, 0, 0]},
        {"id": 6, "position_mm": [0, 2, 0]},
        {"id": 7, "position_mm": [2, 0, 0]},
        {"id": 8, "position_mm": [0, 0, -2]},
        {"id": 9, "position_mm": [0.7, 0.7, 3.5]},
        {"id": 10, "position_mm": [0.5, 0.5, 0.5]},
        {"id": 11, "position_mm": [1.2, 0.5, 0.5]},
        {"id": 12, "position_mm": [0.5, 1.2, 0.8]},
        {"id": 13, "position_mm": [1.2, 1.2, 0.8]},
    ]
    elements = [
        {"id": 1, "structure": "femur", "node_ids": [1, 2, 3, 4]},
        {"id": 2, "structure": "tibia", "node_ids": [5, 6, 7, 8]},
        {"id": 3, "structure": "femoral_cartilage", "node_ids": [1, 3, 2, 9]},
        {"id": 4, "structure": "medial_tibial_cartilage", "node_ids": [5, 7, 6, 10]},
        {"id": 5, "structure": "lateral_tibial_cartilage", "node_ids": [5, 7, 6, 11]},
        {"id": 6, "structure": "medial_meniscus", "node_ids": [5, 7, 6, 12]},
        {"id": 7, "structure": "lateral_meniscus", "node_ids": [5, 7, 6, 13]},
    ]
    included = [*structures, "acl", "pcl", "mcl", "lcl"]
    return {
        "schema_version": "1.0.0",
        "reconstruction_id": str(reconstruction_id),
        "version": "cc0-synthetic-flexion-v1",
        "adapter_id": "febio-4.12",
        "coordinate_system": {
            "name": coordinate_system,
            "unit": "mm",
            "handedness": "right-handed",
            "laterality": laterality,
        },
        "nodes": nodes,
        "elements": elements,
        "surfaces": [
            {
                "name": "femoral_contact",
                "facets": [
                    {"node_ids": [1, 2, 9]},
                    {"node_ids": [2, 3, 9]},
                    {"node_ids": [3, 1, 9]},
                ],
            },
            {
                "name": "tibial_contact",
                "facets": [
                    {"node_ids": [5, 7, 10]},
                    {"node_ids": [7, 6, 10]},
                    {"node_ids": [6, 5, 10]},
                ],
            },
        ],
        "node_sets": [
            {"name": "femur_control", "node_ids": [1, 2, 3, 4]},
            {"name": "tibia_fixed", "node_ids": [5, 6, 7, 8]},
        ],
        "ligament_attachments": [
            {"name": "acl", "origin_node_id": 1, "insertion_node_id": 5},
            {"name": "pcl", "origin_node_id": 2, "insertion_node_id": 7},
            {"name": "mcl", "origin_node_id": 3, "insertion_node_id": 6},
            {"name": "lcl", "origin_node_id": 1, "insertion_node_id": 5},
        ],
        "included_structures": included,
        "excluded_structures": [
            item for item in REQUIRED_KNEE_STRUCTURES if item not in included
        ],
        "source": "Generated Knee Twin synthetic geometry; not anatomical evidence.",
        "license": "CC0-1.0",
    }
