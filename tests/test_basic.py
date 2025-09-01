"""Basic tests for Geberit Aquaclean integration."""

def test_import():
    """Test that the integration can be imported."""
    from custom_components.geberit_aquaclean import DOMAIN
    assert DOMAIN == "geberit_aquaclean"
