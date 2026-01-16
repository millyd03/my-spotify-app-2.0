import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ruleset_crud(test_app):
    """Test creating, confirming, deleting, and validating removal of a 'Last Year' ruleset."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
    # Step 1: Create the ruleset
    ruleset_data = {
        "name": "Last Year",
        "keywords": ["last year", "previous year"],
        "description": "Songs released in the previous calendar year",
        "criteria": {"min_year": 2025, "max_year": 2025}
    }
    response = await client.post("/api/rulesets", json=ruleset_data)
    assert response.status_code == 201, f"Failed to create ruleset: {response.text}"
    
    ruleset = response.json()
    assert ruleset["name"] == "Last Year"
    assert ruleset["keywords"] == ["last year", "previous year"]
    assert ruleset["description"] == "Songs released in the previous calendar year"
    assert ruleset["criteria"] == {"min_year": 2025, "max_year": 2025}
    ruleset_id = ruleset["id"]
    
    # Step 2: Confirm creation by listing rulesets
    response = await client.get("/api/rulesets")
    assert response.status_code == 200, f"Failed to list rulesets: {response.text}"
    
    rulesets = response.json()
    assert isinstance(rulesets, list), "Rulesets response should be a list"
    assert any(r["id"] == ruleset_id for r in rulesets), "Created ruleset not found in list"
    
    # Step 3: Delete the ruleset
    response = await client.delete(f"/api/rulesets/{ruleset_id}")
    assert response.status_code == 200, f"Failed to delete ruleset: {response.text}"
    
    # Step 4: Validate deletion
    # Check that getting the ruleset by ID returns 404
    response = await client.get(f"/api/rulesets/{ruleset_id}")
    assert response.status_code == 404, f"Ruleset should not exist after deletion: {response.text}"
    
    # Check that it's not in the list anymore
    response = await client.get("/api/rulesets")
    assert response.status_code == 200, f"Failed to list rulesets after deletion: {response.text}"
    
    rulesets = response.json()
    assert not any(r["id"] == ruleset_id for r in rulesets), "Deleted ruleset still found in list"