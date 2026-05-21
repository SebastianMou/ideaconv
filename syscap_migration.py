"""
Syscap to Django Migration Script
==================================
This script fetches data from Syscap API and transforms it to match your Django models.

Requirements:
    pip install requests python-dotenv

Setup:
    1. Create a .env file with your Syscap API token:
       SYSCAP_API_TOKEN=your_token_here

    2. Run the script:
       python syscap_migration.py

Output:
    - syscap_export.json (raw data from Syscap)
    - django_fixtures.json (transformed data ready for Django import)
"""

import requests
import json
from datetime import datetime, date
from decimal import Decimal
import time
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv('core/.env')

# Configuration
SYSCAP_API_BASE = "https://api.syscap.com.mx"
API_TOKEN = os.getenv('SYSCAP_API_TOKEN', '')
RATE_LIMIT_DELAY = 1.5  # seconds between requests to avoid rate limits

# Request headers
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}


class SyscapMigration:
    def __init__(self):
        self.raw_data = {
            'investors': [],
            'promoters': [],
            'prospects': [],
            'promissory_notes': [],
            'transactions': {},
            'statements': {},
            'payments': []
        }
        self.django_data = []
        self.id_mapping = {
            'promoters': {},  # syscap_id -> django_pk
            'investors': {},
            'promissory_notes': {},
        }
        self.next_pk = {
            'promoter': 1,
            'investor': 1,
            'investment': 1,
            'movement': 1,
            'statement': 1,
            'payment': 1,
            'prospect': 1
        }

    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a request to Syscap API with rate limiting"""
        url = f"{SYSCAP_API_BASE}{endpoint}"
        try:
            print(f"Fetching: {endpoint}")
            response = requests.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            time.sleep(RATE_LIMIT_DELAY)  # Respect rate limits
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {endpoint}: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return {}

    def _paginated_request(self, endpoint: str, per_page: int = 100) -> List:
        """Fetch all pages from a paginated endpoint"""
        all_data = []
        page = 1

        while True:
            params = {'page': page, 'per': per_page}
            data = self._request(endpoint, params)

            if not data or not isinstance(data, dict):
                break

            # Handle different response structures
            items = data.get('data', data.get('investors', data.get('promoters', data.get('prospects', []))))

            if not items:
                break

            all_data.extend(items)

            # Check if there are more pages
            if len(items) < per_page:
                break

            page += 1

        return all_data

    def fetch_all_data(self):
        """Fetch all data from Syscap API"""
        print("\n" + "="*60)
        print("FETCHING DATA FROM SYSCAP API")
        print("="*60 + "\n")

        # Fetch Promoters
        print("📋 Fetching Promoters...")
        self.raw_data['promoters'] = self._paginated_request('/promoters')
        print(f"   ✓ Found {len(self.raw_data['promoters'])} promoters\n")

        # Fetch Investors
        print("👥 Fetching Investors...")
        self.raw_data['investors'] = self._paginated_request('/investors')
        print(f"   ✓ Found {len(self.raw_data['investors'])} investors")

        # Fetch detailed data for each investor
        print("   📋 Fetching investor details (addresses, contacts, bank accounts, fiscal data)...")
        for investor in self.raw_data['investors']:
            investor_id = investor.get('id')
            if investor_id:
                # Fetch addresses
                addresses = self._request(f'/investors/{investor_id}/addresses')
                investor['addresses'] = addresses.get('data', [])

                # Fetch contacts
                contacts = self._request(f'/investors/{investor_id}/contacts')
                investor['contacts'] = contacts.get('data', [])

                # Fetch bank accounts
                bank_accounts = self._request(f'/investors/{investor_id}/bank_accounts')
                investor['bank_accounts'] = bank_accounts.get('data', [])

                # Fetch fiscal addresses
                fiscal_addresses = self._request(f'/investors/{investor_id}/fiscal_addresses')
                investor['fiscal_addresses'] = fiscal_addresses.get('data', [])
        print(f"   ✓ Fetched detailed data for all investors\n")

        # Fetch Prospects
        print("🎯 Fetching Prospects...")
        self.raw_data['prospects'] = self._paginated_request('/prospects')
        print(f"   ✓ Found {len(self.raw_data['prospects'])} prospects\n")

        # Fetch Promissory Notes
        print("📝 Fetching Promissory Notes...")
        self.raw_data['promissory_notes'] = self._paginated_request('/promissory_notes')
        print(f"   ✓ Found {len(self.raw_data['promissory_notes'])} promissory notes\n")

        # Fetch Transactions for each Promissory Note
        print("💸 Fetching Transactions...")
        for pn in self.raw_data['promissory_notes']:
            pn_id = pn.get('id')
            if pn_id:
                transactions = self._request(f'/promissory_note/{pn_id}/transactions')
                self.raw_data['transactions'][pn_id] = transactions.get('data', [])
        print(f"   ✓ Fetched transactions for {len(self.raw_data['transactions'])} notes\n")

        # Fetch Payments
        print("💰 Fetching Payments...")
        self.raw_data['payments'] = self._paginated_request('/payments')
        print(f"   ✓ Found {len(self.raw_data['payments'])} payments\n")

        # Fetch Monthly Cuts & Statements
        print("📊 Fetching Monthly Cuts & Statements...")
        monthly_cuts = self._paginated_request('/monthly_cuts')
        for cut in monthly_cuts:
            cut_id = cut.get('id')
            if cut_id:
                statements = self._request(f'/monthly_cuts/{cut_id}/statements')
                self.raw_data['statements'][cut_id] = statements.get('data', [])
        print(f"   ✓ Fetched statements for {len(monthly_cuts)} monthly cuts\n")

        # Save raw data
        with open('syscap_export.json', 'w', encoding='utf-8') as f:
            json.dump(self.raw_data, f, indent=2, ensure_ascii=False, default=str)
        print("✅ Raw data saved to: syscap_export.json\n")

    def transform_promoters(self):
        """Transform Syscap promoters to Django Promotor model"""
        print("🔄 Transforming Promoters...")

        for promoter in self.raw_data['promoters']:
            syscap_id = promoter.get('id')
            django_pk = self.next_pk['promoter']
            self.next_pk['promoter'] += 1
            self.id_mapping['promoters'][syscap_id] = django_pk

            self.django_data.append({
                'model': 'inversiones.promotor',
                'pk': django_pk,
                'fields': {
                    'nombre': promoter.get('name', ''),
                    'telefono': promoter.get('phone', ''),
                    'correo': promoter.get('email', ''),
                    'activo': promoter.get('status') == 'active',
                    'fecha_registro': promoter.get('created_at', date.today().isoformat())[:10]
                }
            })

        print(f"   ✓ Transformed {len(self.raw_data['promoters'])} promoters\n")

    def transform_investors(self):
        """Transform Syscap investors to Django Inversionista model"""
        print("🔄 Transforming Investors...")

        for investor in self.raw_data['investors']:
            syscap_id = investor.get('id')
            django_pk = self.next_pk['investor']
            self.next_pk['investor'] += 1
            self.id_mapping['investors'][syscap_id] = django_pk

            # Map promoter
            promoter_id = investor.get('promoter_id')
            promoter_fk = self.id_mapping['promoters'].get(promoter_id)

            # Map tipo_contribuyente
            investor_type = investor.get('investor_type', 'natural_person')
            tipo_contribuyente = 'fisica' if investor_type == 'natural_person' else 'moral'

            # Map civil status
            civil_status_map = {
                'single': 'soltero',
                'married': 'casado',
                'divorced': 'divorciado',
                'widowed': 'viudo'
            }
            estado_civil = civil_status_map.get(investor.get('civil_status', 'single'), 'soltero')

            # Map document type
            doc_type_map = {
                'ine': 'ine',
                'passport': 'pasaporte',
                'professional_id': 'cedula'
            }
            tipo_documento = doc_type_map.get(investor.get('id_type', 'ine'), 'ine')

            # Extract data from nested endpoints
            addresses = investor.get('addresses', [])
            address = addresses[0] if addresses else {}

            contacts = investor.get('contacts', [])
            primary_contact = contacts[0] if contacts else {}

            bank_accounts = investor.get('bank_accounts', [])
            primary_bank = bank_accounts[0] if bank_accounts else {}

            fiscal_addresses = investor.get('fiscal_addresses', [])
            primary_fiscal = fiscal_addresses[0] if fiscal_addresses else {}

            # Build address from available data (addresses or fiscal)
            address_data = address if address else primary_fiscal
            street_parts = []
            if address_data.get('street'):
                street_parts.append(address_data['street'])
            if address_data.get('street_number'):
                street_parts.append(address_data['street_number'])
            full_street = ' '.join(street_parts)

            self.django_data.append({
                'model': 'inversiones.inversionista',
                'pk': django_pk,
                'fields': {
                    'tipo_contribuyente': tipo_contribuyente,
                    'es_entidad_financiera': investor.get('is_financial_entity', False),
                    'nombre_completo': investor.get('full_name', investor.get('name', '')),
                    'nacionalidad': investor.get('nationality', 'Mexicana'),
                    'curp': (primary_fiscal.get('tax_id_number') or primary_fiscal.get('curp') or investor.get('curp', ''))[:18] or '',
                    'fecha_nacimiento': investor.get('birth_date', '')[:10] or None,
                    'correo': primary_contact.get('email') or investor.get('email', ''),
                    'telefono': primary_contact.get('phone') or primary_contact.get('mobile_phone') or investor.get('phone', ''),
                    'fecha_ingreso': investor.get('created_at', date.today().isoformat())[:10],
                    'tipo_documento': tipo_documento,
                    'numero_documento': investor.get('id_number', ''),
                    'estado_civil': estado_civil,
                    
                    # Domicilio - from addresses or fiscal address
                    'calle': full_street,
                    'ciudad': address_data.get('city', ''),
                    'estado': address_data.get('state', ''),
                    'codigo_postal': address_data.get('postal_code') or address_data.get('zip_code', ''),
                    
                    # Datos fiscales - get from fiscal_addresses endpoint
                    'rfc': (primary_fiscal.get('tax_id_number') or primary_fiscal.get('rfc') or investor.get('rfc', ''))[:13] or '',
                    'regimen_fiscal': primary_fiscal.get('regime') or investor.get('fiscal_regime', 'Régimen de Intereses'),
                    'nombre_fiscal': primary_fiscal.get('business_name') or investor.get('fiscal_name', investor.get('full_name', '')),
                    'pais_fiscal': primary_fiscal.get('country') or investor.get('fiscal_country', 'México'),
                    'estado_fiscal': primary_fiscal.get('state') or investor.get('fiscal_state', ''),
                    'cp_fiscal': primary_fiscal.get('postal_code') or address_data.get('zip_code', ''),
                    
                    # Datos bancarios - get from bank_accounts endpoint
                    'banco': self._map_bank(primary_bank.get('bank_name', '')),
                    'clabe': primary_bank.get('clabe', '')[:18] or '',
                    
                    'eliminado': investor.get('deleted', False),
                    'fecha_eliminado': investor.get('deleted_at'),
                    'promotor': promoter_fk
                }
            })

        print(f"   ✓ Transformed {len(self.raw_data['investors'])} investors\n")

    def _map_bank(self, bank_name: str) -> str:
        """Map Syscap bank names to Django choices"""
        if not bank_name:  # Handle None or empty string
            return 'otro'
        
        bank_map = {
            'bbva': 'bbva',
            'bancomer': 'bbva',
            'banorte': 'banorte',
            'hsbc': 'hsbc',
            'santander': 'santander',
            'banamex': 'banamex',
            'citibanamex': 'banamex'
        }
        bank_lower = bank_name.lower()

    def transform_promissory_notes(self):
        """Transform Syscap promissory notes to Django Inversion model"""
        print("🔄 Transforming Promissory Notes...")

        for pn in self.raw_data['promissory_notes']:
            syscap_id = pn.get('id')
            django_pk = self.next_pk['investment']
            self.next_pk['investment'] += 1
            self.id_mapping['promissory_notes'][syscap_id] = django_pk

            # Map investor
            investor_id = pn.get('investor_id')
            investor_fk = self.id_mapping['investors'].get(investor_id)

            if not investor_fk:
                print(f"   ⚠️  Warning: Promissory note {syscap_id} has no valid investor")
                continue

            # Map status
            status_map = {
                'active': 'activo',
                'matured': 'vencido',
                'about_to_mature': 'por_vencer'
            }
            estado = status_map.get(pn.get('status'), 'activo')

            # Calculate base from interest calculation method
            base_calculo = 360 if pn.get('interest_base') == '360' else 365

            self.django_data.append({
                'model': 'inversiones.inversion',
                'pk': django_pk,
                'fields': {
                    'inversionista': investor_fk,
                    'capital': str(pn.get('amount', pn.get('balance', 0))),
                    'tasa_anual': str(pn.get('interest_rate', 0)),
                    'base_calculo': base_calculo,
                    'porcentaje_factura': str(pn.get('invoice_percentage', 100)),
                    'fecha_inicio': pn.get('start_date', date.today().isoformat())[:10],
                    'fecha_vencimiento': pn.get('end_date', '')[:10] or None,
                    'estado': estado,
                    'notas': pn.get('notes', '')
                }
            })

        print(f"   ✓ Transformed {len(self.raw_data['promissory_notes'])} promissory notes\n")

    def transform_transactions(self):
        """Transform Syscap transactions to Django Movimiento model"""
        print("🔄 Transforming Transactions...")

        count = 0
        for pn_id, transactions in self.raw_data['transactions'].items():
            investment_fk = self.id_mapping['promissory_notes'].get(pn_id)

            if not investment_fk:
                continue

            for trans in transactions:
                django_pk = self.next_pk['movement']
                self.next_pk['movement'] += 1

                # Map transaction type
                tipo_map = {
                    'deposit': 'abono',
                    'withdrawal': 'retiro',
                    'abono': 'abono',
                    'retiro': 'retiro'
                }
                tipo = tipo_map.get(trans.get('type', 'deposit'), 'abono')

                self.django_data.append({
                    'model': 'inversiones.movimiento',
                    'pk': django_pk,
                    'fields': {
                        'inversion': investment_fk,
                        'tipo': tipo,
                        'monto': str(trans.get('amount', 0)),
                        'fecha': trans.get('date', date.today().isoformat())[:10],
                        'notas': trans.get('notes', ''),
                        'fecha_registro': trans.get('created_at', datetime.now().isoformat())
                    }
                })
                count += 1

        print(f"   ✓ Transformed {count} transactions\n")

    def transform_prospects(self):
        """Transform Syscap prospects to Django Prospecto model"""
        print("🔄 Transforming Prospects...")

        for prospect in self.raw_data['prospects']:
            django_pk = self.next_pk['prospect']
            self.next_pk['prospect'] += 1

            # Map promoter
            promoter_id = prospect.get('promoter_id')
            promoter_fk = self.id_mapping['promoters'].get(promoter_id)

            # Map stage
            stage_map = {
                'initial': 'inicial',
                'follow_up': 'seguimiento',
                'ready': 'listo'
            }
            etapa = stage_map.get(prospect.get('stage', 'initial'), 'inicial')

            # Check if converted
            investor_id = prospect.get('investor_id')
            investor_fk = self.id_mapping['investors'].get(investor_id) if investor_id else None

            self.django_data.append({
                'model': 'inversiones.prospecto',
                'pk': django_pk,
                'fields': {
                    'nombre_completo': prospect.get('full_name', prospect.get('name', '')),
                    'telefono': prospect.get('phone', ''),
                    'correo': prospect.get('email', ''),
                    'monto_estimado': str(prospect.get('estimated_amount', 0)) if prospect.get('estimated_amount') else None,
                    'promotor': promoter_fk,
                    'etapa': etapa,
                    'notas': prospect.get('notes', ''),
                    'fecha_registro': prospect.get('created_at', date.today().isoformat())[:10],
                    'convertido': bool(investor_fk),
                    'inversionista': investor_fk
                }
            })

        print(f"   ✓ Transformed {len(self.raw_data['prospects'])} prospects\n")

    def transform_statements_and_payments(self):
        """Transform Syscap statements and payments to Django EstadoDeCuenta and Pago models"""
        print("🔄 Transforming Statements & Payments...")

        statement_count = 0
        payment_count = 0

        for cut_id, statements in self.raw_data['statements'].items():
            for statement in statements:
                # Map investor
                investor_id = statement.get('investor_id')
                investor_fk = self.id_mapping['investors'].get(investor_id)

                if not investor_fk:
                    continue

                # Create EstadoDeCuenta
                statement_pk = self.next_pk['statement']
                self.next_pk['statement'] += 1

                # Map status
                status_map = {
                    'generated': 'generado',
                    'sent': 'enviado',
                    'pending': 'pendiente'
                }
                estado = status_map.get(statement.get('status', 'pending'), 'pendiente')

                self.django_data.append({
                    'model': 'inversiones.estadodecuenta',
                    'pk': statement_pk,
                    'fields': {
                        'inversionista': investor_fk,
                        'inversion': None,  # New model links to investor, not individual investment
                        'periodo_inicio': statement.get('period_start', date.today().isoformat())[:10],
                        'periodo_fin': statement.get('period_end', date.today().isoformat())[:10],
                        'dias_periodo': statement.get('days', 30),
                        'interes_bruto': str(statement.get('gross_interest', 0)),
                        'isr': str(statement.get('isr', 0)),
                        'iva': str(statement.get('iva', 0)),
                        'interes_neto': str(statement.get('net_interest', 0)),
                        'pago_externo': str(statement.get('external_payment', 0)),
                        'total_pagar': str(statement.get('total_payable', 0)),
                        'estado': estado,
                        'notas': statement.get('notes', '')
                    }
                })
                statement_count += 1

                # Create associated Pago if payment exists
                payment_info = statement.get('payment')
                if payment_info or statement.get('paid'):
                    payment_pk = self.next_pk['payment']
                    self.next_pk['payment'] += 1

                    # Map payment method
                    method_map = {
                        'bank_transfer': 'transferencia',
                        'cash': 'efectivo',
                        'union': 'sindicato'
                    }
                    metodo = method_map.get(payment_info.get('method') if payment_info else None, 'transferencia')

                    # Map payment status
                    pago_estado = 'pagado' if statement.get('paid') else 'pendiente'

                    self.django_data.append({
                        'model': 'inversiones.pago',
                        'pk': payment_pk,
                        'fields': {
                            'estado_de_cuenta': statement_pk,
                            'metodo': metodo,
                            'fecha_pago': (payment_info.get('payment_date') if payment_info else None) or None,
                            'estado': pago_estado,
                            'folio': payment_info.get('folio', '') if payment_info else '',
                            'notas': payment_info.get('notes', '') if payment_info else '',
                            'confirmado_por': payment_info.get('confirmed_by', '') if payment_info else ''
                        }
                    })
                    payment_count += 1

        print(f"   ✓ Transformed {statement_count} statements")
        print(f"   ✓ Transformed {payment_count} payments\n")

    def run_migration(self):
        """Run the complete migration process"""
        print("\n" + "="*60)
        print("SYSCAP TO DJANGO MIGRATION")
        print("="*60 + "\n")

        # Fetch data
        self.fetch_all_data()

        # Transform data
        print("="*60)
        print("TRANSFORMING DATA")
        print("="*60 + "\n")

        self.transform_promoters()
        self.transform_investors()
        self.transform_promissory_notes()
        self.transform_transactions()
        self.transform_prospects()
        self.transform_statements_and_payments()

        # Save Django fixtures
        with open('django_fixtures.json', 'w', encoding='utf-8') as f:
            json.dump(self.django_data, f, indent=2, ensure_ascii=False)

        print("="*60)
        print("MIGRATION COMPLETE")
        print("="*60 + "\n")
        print(f"📦 Django fixtures saved to: django_fixtures.json")
        print(f"📊 Total records transformed: {len(self.django_data)}")
        print("\nNext steps:")
        print("1. Review django_fixtures.json")
        print("2. Run: python manage.py import_syscap django_fixtures.json")
        print("3. Verify data in Django admin")
        print("\n")


if __name__ == '__main__':
    if not API_TOKEN:
        print("❌ ERROR: SYSCAP_API_TOKEN not found in environment variables")
        print("Please create a .env file with your token:")
        print("SYSCAP_API_TOKEN=your_token_here")
        exit(1)

    migration = SyscapMigration()
    migration.run_migration()
