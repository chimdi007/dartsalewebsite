from flask import Flask, Blueprint, send_file, request, jsonify
from fpdf import FPDF
from io import BytesIO
import mysql.connector
from datetime import datetime


# Define the Blueprint
comms_bp = Blueprint('comms', __name__)

currency = ""

def config_db():
        connection = mysql.connector.connect(
            host='192.168.1.100',
            user='dartboss',
            password='Blackcat111@',
            database='dartsale'
        )
        return connection

class Statement(FPDF):
    def __init__(self, transactions):
        super().__init__('L', 'mm', 'A4')
        self.transactions = transactions
        self.add_page()
        self.set_font('Arial', 'B', 12)
        self.create_pdf()

    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Transaction Statement', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def create_pdf(self):
        try:
            headers = ['Date', 'Receipt Number', 'Attendant', 'Transaction Type', 'Price', 'VAT', 'Total']
            col_widths = [30, 40, 40, 40, 30, 30, 30]

            self.set_font('Arial', 'B', 10)
            for header, col_width in zip(headers, col_widths):
                self.cell(col_width, 10, header, 1)
            self.ln()
            
            # Initialize sums
            total_price = 0
            total_vat = 0
            total_overall = 0

            self.set_font('Arial', '', 10)
            if not self.transactions:
                print("No transactions to display.")
            for transaction in self.transactions:
                self.cell(col_widths[0], 10, transaction['date'], 1)
                self.cell(col_widths[1], 10, transaction['receipt_number'], 1)
                self.cell(col_widths[2], 10, transaction['attendant'], 1)
                self.cell(col_widths[3], 10, transaction['transaction_type'], 1)
                self.cell(col_widths[4], 10, f"${transaction['price']:.2f}", 1)
                self.cell(col_widths[5], 10, f"${transaction['vat']:.2f}", 1)
                self.cell(col_widths[6], 10, f"${transaction['total']:.2f}", 1)
                self.ln()
                
                # Update sums
                total_price += transaction['price']
                total_vat += transaction['vat']
                total_overall += transaction['total']
                
            self.set_font('Arial', 'B', 10)
            self.cell(sum(col_widths[:4]), 10, 'Total', 1, align='R')
            self.cell(col_widths[4], 10, f"${total_price:.2f}", 1)
            self.cell(col_widths[5], 10, f"${total_vat:.2f}", 1)
            self.cell(col_widths[6], 10, f"${total_overall:.2f}", 1)
            self.ln()
        except Exception as e:
            print(f"Error during PDF creation: {e}")



    def get_pdf(self):
        pdf_output = BytesIO()
        pdf_data = self.output(dest='S').encode('latin1')  # Get PDF data as bytes
        pdf_output.write(pdf_data)  # Write the PDF data to BytesIO object
        pdf_output.seek(0)  # Reset the buffer's pointer to the start
        pdf_size = len(pdf_output.getvalue())  # Get the size of the buffer
        print("PDF SIZE: ", pdf_size)
        return pdf_output






@comms_bp.route('/download_transaction_statement', methods=['GET'])
def download_transaction_statement():
    global currency
    try:
        user_unique_id = request.args.get('user_unique_id')
        shop_key = request.args.get('shop_key')
        shop_name = request.args.get('shop_name')
        currency = request.args.get('currency')
        startdate_str = request.args.get('startdate') + ' 00:00'
        enddate_str = request.args.get('enddate') + ' 00:00'
        startdate = datetime.strptime(startdate_str, '%Y-%m-%d %H:%M')
        enddate = datetime.strptime(enddate_str, '%Y-%m-%d %H:%M')
        
        print("ID:", user_unique_id, shop_key, shop_name)
        print("DATES: ", startdate, enddate)
        print ("Currency: ", currency)

        # Establish the database connection
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("SELECT date, receipt_number, attendant, transaction_type FROM sales WHERE user_unique_id=%s AND shop_key=%s AND date>=%s AND date<=%s", (user_unique_id, shop_key, startdate, enddate))
        data = cursor.fetchall()

        transactions = []
        if data:
            for row in data:
                transactions.append({
                    'date': row[0].strftime('%Y-%m-%d %H:%M'),   # Assuming the first column is the date
                    'receipt_number': row[1],  # Assuming the second column is the receipt number
                    'attendant': row[2],  # Assuming the third column is the attendant
                    'transaction_type': row[3],  # Assuming the fourth column is the transaction type
                    'price': 100.0,
                    'vat': 5.0,
                    'total': 105.0
                })
        else:
            return jsonify(message="No records found!")

        print("Transactions: ", transactions)
        statement = Statement(transactions)
        pdf_output = statement.get_pdf()
        return send_file(pdf_output, download_name='transaction_statement.pdf', as_attachment=True)
    except ValueError as ve:
        print("ValueError: ", str(ve))
        return jsonify(message="Invalid date format"), 400
    except Exception as e:
        print("Error: ", str(e))
        return jsonify(message="An error occurred while processing the request"), 500



























def download_transaction_statement2():
    transactions = [
        {
            'date': '2024-06-08',
            'receipt_number': '12345',
            'attendant': 'John Doe',
            'transaction_type': 'Credit',
            'price': 100.0,
            'vat': 5.0,
            'total': 105.0
        },
        {
            'date': '2024-06-09',
            'receipt_number': '12346',
            'attendant': 'Jane Doe',
            'transaction_type': 'Debit',
            'price': 50.0,
            'vat': 2.5,
            'total': 52.5
        }
    ]

    statement = Statement(transactions)
    pdf_output = statement.get_pdf()
    return send_file(pdf_output, download_name='transaction_statement.pdf', as_attachment=True)
