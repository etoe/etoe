from etoe.serialization import (
    decode_base64url_identifier,
    decode_identifier,
    encode_base64url_identifier,
    encode_identifier,
)


def test_hex_identifier_roundtrip_and_python_identifier():
    source = "Æ2.b.s.br-{id=1}-(æ:s|æ:f)"
    encoded = encode_identifier(source)
    assert encoded.isidentifier()
    assert decode_identifier(encoded) == source


def test_base64url_identifier_roundtrip():
    source = "τ.physics.kinematic.Æ2.b"
    encoded = encode_base64url_identifier(source)
    assert encoded.isidentifier()
    assert decode_base64url_identifier(encoded) == source
