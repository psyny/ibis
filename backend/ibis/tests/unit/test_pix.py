"""domain/pix.py must match the frontend (utils/pixKey.ts, utils/pix.ts): same keys, same codes."""
import pytest

from domain.pix import PixKey, crc16, parse_pix_key, payment_page_url, pix_code

# Made by the frontend's library (react-qrcode-pix) for the same input
FRONTEND_CODES = [
    ("rafael@example.com", "Rafaél Ção da Silva Júnior Neto", 5,
     "00020126400014BR.GOV.BCB.PIX0118rafael@example.com52040000530398654045.005802BR5925Rafael Cao da Silva Junio6006BRASIL62070503***63041845"),
    ("+5521993815159", "Ana", 12.5,
     "00020126360014BR.GOV.BCB.PIX0114+5521993815159520400005303986540512.505802BR5903Ana6006BRASIL62070503***6304E3AD"),
    ("52998224725", "Mia", 30,
     "00020126330014BR.GOV.BCB.PIX011152998224725520400005303986540530.005802BR5903Mia6006BRASIL62070503***6304B770"),
    ("123e4567-e89b-12d3-a456-426614174000", "José", 1234.56,
     "00020126580014BR.GOV.BCB.PIX0136123e4567-e89b-12d3-a456-42661417400052040000530398654071234.565802BR5904Jose6006BRASIL62070503***63047A72"),
    ("11222333000181", "", None,
     "00020126360014BR.GOV.BCB.PIX0114112223330001815204000053039865802BR5909RECEBEDOR6006BRASIL62070503***6304549A"),
]


@pytest.mark.parametrize("raw,name,amount,expected", FRONTEND_CODES)
def test_codes_match_the_frontend(raw, name, amount, expected):
    key = parse_pix_key(raw)
    assert pix_code(key, name, amount) == expected
    assert expected[-4:] == crc16(expected[:-4])


@pytest.mark.parametrize(
    "raw",
    [
        "+55 21 99381-5159",
        "+55 (21) 99381-5159",
        "(21) 99381-5159",
        "21993815159",
        "021 99381-5159",
        "5521993815159",
        "55 21 99381 5159",
        " +55 21 99381-5159​",
    ],
)
def test_phones_in_common_formats(raw):
    assert parse_pix_key(raw) == PixKey("phone", "+5521993815159")


def test_documents_emails_and_random_keys():
    assert parse_pix_key("529.982.247-25") == PixKey("cpf", "52998224725")
    assert parse_pix_key("11.222.333/0001-81") == PixKey("cnpj", "11222333000181")
    assert parse_pix_key("  Rafael.Silva@Example.COM ") == PixKey("email", "rafael.silva@example.com")
    assert parse_pix_key("mailto:ana@x.com") == PixKey("email", "ana@x.com")
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    assert parse_pix_key(uuid.upper().replace("-", "")) == PixKey("random", uuid)
    assert parse_pix_key("+55 21 3381-5159") == PixKey("phone", "+552133815159")


@pytest.mark.parametrize(
    "raw",
    ["", None, "hello world", "12345", "529.982.247-24", "11.222.333/0001-82", "ana@", "+1 415 555 0100",
     "+55 21 993815-1593", "+55 21 8938-15159", "+55 01 99381-5159"],
)
def test_unusable_keys(raw):
    assert parse_pix_key(raw) is None


def test_payment_page_url():
    url = payment_page_url("https://ibis.example.com/", "mia@x.com", "Mia Souza", 30, "pt-BR")
    assert url == "https://ibis.example.com/pay?key=mia%40x.com&name=Mia+Souza&amount=30.00&lang=pt-BR"
