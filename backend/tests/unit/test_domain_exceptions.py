"""Unit tests for domain exceptions."""

from greencity.domain.exceptions import ConflictError, DomainError, NotFoundError, ValidationError


def test_domain_error_hierarchy() -> None:
    """Specific errors are DomainError subclasses with a message attribute."""

    err = NotFoundError("missing")
    assert isinstance(err, DomainError)
    assert err.message == "missing"
    assert str(ValidationError("bad")) == "bad"
    assert isinstance(ConflictError("clash"), DomainError)
