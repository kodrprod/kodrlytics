"""Script to create test fixture ZIPs. Run once: python -m backend.tests.create_fixtures"""
import io
import zipfile
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)


def create_tiny_co_zip() -> Path:
    """
    Create a minimal company ZIP with German number-formatted accounting CSV,
    payroll CSV, and annual report text.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # Annual report (readable text with P&L in German numbers)
        annual = (
            "Jahresbericht 2023 - TinyCo GmbH\n"
            "Umsatzerlöse:               1.234.567,89 EUR\n"
            "Materialaufwand:              456.789,12 EUR\n"
            "Bruttoergebnis:               777.778,77 EUR\n"
            "Personalkosten:               234.567,00 EUR\n"
            "Sonstige Aufwendungen:         98.765,43 EUR\n"
            "EBIT:                         444.446,34 EUR\n"
            "Zinsen:                        12.345,67 EUR\n"
            "EBT:                          432.100,67 EUR\n"
            "Steuern:                      129.630,20 EUR\n"
            "Jahresüberschuss:             302.470,47 EUR\n\n"
            "Bilanz 31.12.2023\n"
            "Bilanzsumme:                2.000.000,00 EUR\n"
            "Eigenkapital:                 800.000,00 EUR\n"
            "Fremdkapital:               1.200.000,00 EUR\n"
        )
        zf.writestr("TinyCo_GmbH/jahresbericht/2023_annual.txt", annual)

        # Accounting journal (German locale CSV)
        accounting_csv = (
            "Buchungsdatum;Kontonummer;Buchungstext;Betrag\n"
            "2023-01-15;4000;Umsatzerlöse Projekt A;45.678,90\n"
            "2023-01-22;4000;Umsatzerlöse Projekt B;32.456,78\n"
            "2023-02-10;5000;Materialaufwand;-18.234,56\n"
            "2023-02-15;4000;Umsatzerlöse Projekt C;67.890,12\n"
            "2023-03-01;6000;Personalkosten;-19.567,89\n"
        )
        zf.writestr("TinyCo_GmbH/buchhaltung/2023_journal.csv", accounting_csv)

        # Payroll journal
        payroll_csv = (
            "Monat;Mitarbeiter;Bruttogehalt;Sozialversicherung;Auszahlung\n"
            "2023-01;10;19.567,89;3.913,58;15.654,31\n"
            "2023-02;10;19.567,89;3.913,58;15.654,31\n"
            "2023-03;11;21.234,56;4.246,91;16.987,65\n"
        )
        zf.writestr("TinyCo_GmbH/personal/2023_payroll.csv", payroll_csv)

    path = FIXTURES_DIR / "tiny_co.zip"
    path.write_bytes(buf.getvalue())
    print(f"Created {path} ({path.stat().st_size} bytes)")
    return path


if __name__ == "__main__":
    create_tiny_co_zip()
