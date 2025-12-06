import json
import os
from datetime import datetime, timedelta
import math

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import ttk, messagebox, filedialog, simpledialog

# Matplotlib for charts
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Optional PDF export
try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    HAS_FPDF = False

DATA_FILE = 'expenses.json'
DEFAULT_THEME = 'darkly'

# ---------------------- Backend ----------------------

def load_expenses():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_expenses(expenses):
    with open(DATA_FILE, 'w') as f:
        json.dump(expenses, f, indent=4)


def backup_json(path):
    expenses = load_expenses()
    with open(path, 'w') as f:
        json.dump(expenses, f, indent=4)


def restore_json(path):
    with open(path, 'r') as f:
        data = json.load(f)
    save_expenses(data)
    return data


def export_csv(expenses, filename='expenses.csv'):
    import csv
    if not expenses:
        raise ValueError('No expenses to export')
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'category', 'amount', 'note'])
        writer.writeheader()
        for exp in expenses:
            writer.writerow({
                'date': exp.get('date',''),
                'category': exp.get('category',''),
                'amount': exp.get('amount',''),
                'note': exp.get('note','')
            })


def export_pdf_summary(expenses, filename='expenses_summary.pdf'):
    # Create a simple PDF summary; if fpdf not installed, fallback to text file
    total_all = sum(float(e.get('amount',0)) for e in expenses)
    total_month = sum(float(e.get('amount',0)) for e in expenses if is_in_month(e.get('date')))
    total_today = sum(float(e.get('amount',0)) for e in expenses if is_today(e.get('date')))

    if HAS_FPDF:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Expense Tracker Summary', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.ln(4)
        pdf.cell(0, 8, f'Total (all time): {total_all}', ln=True)
        pdf.cell(0, 8, f'Total (this month): {total_month}', ln=True)
        pdf.cell(0, 8, f'Total (today): {total_today}', ln=True)
        pdf.ln(6)
        pdf.cell(0, 8, 'Top expenses:', ln=True)
        sorted_exp = sorted(expenses, key=lambda x: float(x.get('amount',0)), reverse=True)[:10]
        for e in sorted_exp:
            pdf.multi_cell(0, 7, f"{e.get('date')} | {e.get('category')} | {e.get('amount')} | {e.get('note')}")
        pdf.output(filename)
    else:
        # fallback to text summary
        with open(filename.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
            f.write('Expense Tracker Summary\n')
            f.write(f'Total (all time): {total_all}\n')
            f.write(f'Total (this month): {total_month}\n')
            f.write(f'Total (today): {total_today}\n')
            f.write('\nTop expenses:\n')
            sorted_exp = sorted(expenses, key=lambda x: float(x.get('amount',0)), reverse=True)[:20]
            for e in sorted_exp:
                f.write(f"{e.get('date')} | {e.get('category')} | {e.get('amount')} | {e.get('note')}\n")

# ---------------------- Helpers ----------------------

def parse_date(s):
    # Accept DD-MM-YYYY or YYYY-MM-DD
    if not s: return None
    for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def fmt_date(dt):
    return dt.strftime('%d-%m-%Y')


def is_today(sdate):
    d = parse_date(sdate)
    if not d: return False
    now = datetime.now()
    return d.date() == now.date()


def is_in_month(sdate, ref=None):
    d = parse_date(sdate)
    if not d: return False
    if ref is None:
        ref = datetime.now()
    return d.year == ref.year and d.month == ref.month

# ---------------------- GUI App ----------------------

class ExpenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Expense Tracker - Modern')
        self.root.geometry('1100x620')
        self.expenses = load_expenses()
        self.style = tb.Style()
        self.current_theme = DEFAULT_THEME
        self.budget = None  # monthly budget

        self.build_ui()
        self.refresh_table()
        self.update_dashboard()

    def build_ui(self):
        # Top bar with title and theme switch
        top = tb.Frame(self.root, padding=8)
        top.pack(side='top', fill='x')
        tb.Label(top, text='Expense Tracker', font=('Helvetica', 18, 'bold')).pack(side='left')

        # Theme switcher
        themes = sorted(self.style.theme_names())
        self.theme_var = tb.StringVar(value=self.current_theme)
        theme_menu = tb.OptionMenu(top, self.theme_var, *themes, command=self.change_theme)
        theme_menu.pack(side='right')

        # Main frames: left for controls, center for table, right for charts/dashboard
        main = tb.Frame(self.root)
        main.pack(fill='both', expand=True, padx=8, pady=8)

        left = tb.Frame(main, width=320, padding=10)
        left.pack(side='left', fill='y')

        center = tb.Frame(main, padding=6)
        center.pack(side='left', expand=True, fill='both')

        right = tb.Frame(main, width=360, padding=10)
        right.pack(side='right', fill='y')

        # Left: inputs
        tb.Label(left, text='Add / Edit Expense', font=('Helvetica', 14, 'bold')).pack(pady=6)
        tb.Label(left, text='Date (DD-MM-YYYY)').pack(anchor='w')
        self.date_entry = tb.Entry(left)
        self.date_entry.pack(fill='x', pady=4)

        tb.Label(left, text='Category').pack(anchor='w')
        self.category_entry = tb.Entry(left)
        self.category_entry.pack(fill='x', pady=4)

        tb.Label(left, text='Amount').pack(anchor='w')
        self.amount_entry = tb.Entry(left)
        self.amount_entry.pack(fill='x', pady=4)

        tb.Label(left, text='Note').pack(anchor='w')
        self.note_entry = tb.Entry(left)
        self.note_entry.pack(fill='x', pady=4)

        # Buttons for add/edit
        btn_frame = tb.Frame(left)
        btn_frame.pack(fill='x', pady=6)
        tb.Button(btn_frame, text='Add Expense', bootstyle=SUCCESS, command=self.add_expense).pack(side='left', expand=True, fill='x', padx=2)
        tb.Button(btn_frame, text='Edit Selected', bootstyle=INFO, command=self.edit_selected).pack(side='left', expand=True, fill='x', padx=2)

        tb.Button(left, text='Delete Selected', bootstyle=DANGER, command=self.delete_selected).pack(fill='x', pady=6)

        # Budget box
        tb.Separator(left).pack(fill='x', pady=6)
        tb.Label(left, text='Monthly Budget (optional)').pack(anchor='w')
        bud_frame = tb.Frame(left)
        bud_frame.pack(fill='x')
        self.budget_entry = tb.Entry(bud_frame)
        self.budget_entry.pack(side='left', fill='x', expand=True, pady=4)
        tb.Button(bud_frame, text='Set', bootstyle=PRIMARY, command=self.set_budget).pack(side='left', padx=4)
        tb.Button(left, text='Clear Budget', bootstyle=SECONDARY, command=self.clear_budget).pack(fill='x')

        # Backup / Restore / Export
        tb.Separator(left).pack(fill='x', pady=6)
        tb.Label(left, text='Data / Export').pack(anchor='w')
        tb.Button(left, text='Export CSV', bootstyle=INFO, command=self.export_csv_ui).pack(fill='x', pady=4)
        tb.Button(left, text='Export PDF', bootstyle=INFO, command=self.export_pdf_ui).pack(fill='x', pady=4)
        tb.Button(left, text='Backup JSON', bootstyle=SECONDARY, command=self.backup_ui).pack(fill='x', pady=4)
        tb.Button(left, text='Restore JSON', bootstyle=SECONDARY, command=self.restore_ui).pack(fill='x', pady=4)

        # Center: search, filters, table
        search_frame = tb.Frame(center)
        search_frame.pack(fill='x')
        self.search_var = tb.StringVar()
        tb.Entry(search_frame, textvariable=self.search_var).pack(side='left', fill='x', expand=True, padx=4, pady=4)
        tb.Button(search_frame, text='Search', bootstyle=PRIMARY, command=self.search).pack(side='left', padx=4)
        tb.Button(search_frame, text='Reset', bootstyle=SECONDARY, command=self.reset_filters).pack(side='left')

        filter_frame = tb.Frame(center)
        filter_frame.pack(fill='x')
        tb.Label(filter_frame, text='From (DD-MM-YYYY)').pack(side='left')
        self.from_entry = tb.Entry(filter_frame, width=12)
        self.from_entry.pack(side='left', padx=4)
        tb.Label(filter_frame, text='To (DD-MM-YYYY)').pack(side='left')
        self.to_entry = tb.Entry(filter_frame, width=12)
        self.to_entry.pack(side='left', padx=4)
        tb.Label(filter_frame, text='Category').pack(side='left')
        self.cat_filter = tb.Entry(filter_frame, width=12)
        self.cat_filter.pack(side='left', padx=4)
        tb.Button(filter_frame, text='Apply', bootstyle=PRIMARY, command=self.apply_filters).pack(side='left', padx=4)

        # Table
        columns = ('date','category','amount','note')
        self.tree = ttk.Treeview(center, columns=columns, show='headings', selectmode='browse')
        for c in columns:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=120, anchor='center')

        vsb = ttk.Scrollbar(center, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(center, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.pack(fill='both', expand=True, side='left')
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')

        self.tree.bind('<Double-1>', lambda e: self.edit_selected())

        # Right: Dashboard and charts
        tb.Label(right, text='Dashboard', font=('Helvetica', 14, 'bold')).pack(pady=4)
        self.card_frame = tb.Frame(right)
        self.card_frame.pack(fill='x', pady=4)

        # Cards
        self.today_var = tb.StringVar(value='0')
        self.month_var = tb.StringVar(value='0')
        self.all_var = tb.StringVar(value='0')

        card1 = tb.Frame(self.card_frame, padding=6, bootstyle='info')
        card1.pack(fill='x', pady=4)
        tb.Label(card1, text='Today', font=('Helvetica', 10, 'bold')).pack(anchor='w')
        tb.Label(card1, textvariable=self.today_var, font=('Helvetica', 12)).pack(anchor='w')

        card2 = tb.Frame(self.card_frame, padding=6, bootstyle='primary')
        card2.pack(fill='x', pady=4)
        tb.Label(card2, text='This Month', font=('Helvetica', 10, 'bold')).pack(anchor='w')
        tb.Label(card2, textvariable=self.month_var, font=('Helvetica', 12)).pack(anchor='w')

        card3 = tb.Frame(self.card_frame, padding=6, bootstyle='success')
        card3.pack(fill='x', pady=4)
        tb.Label(card3, text='All Time', font=('Helvetica', 10, 'bold')).pack(anchor='w')
        tb.Label(card3, textvariable=self.all_var, font=('Helvetica', 12)).pack(anchor='w')

        # Buttons for charts
        tb.Separator(right).pack(fill='x', pady=6)
        tb.Button(right, text='Show Category Pie', bootstyle=INFO, command=self.show_pie).pack(fill='x', pady=4)
        tb.Button(right, text='Show Monthly Bars', bootstyle=INFO, command=self.show_monthly_bars).pack(fill='x', pady=4)

    # ---------------------- CRUD ----------------------
    def add_expense(self):
        date = self.date_entry.get().strip()
        if not date:
            date = datetime.now().strftime('%d-%m-%Y')
        # validate date
        if parse_date(date) is None:
            messagebox.showerror('Invalid Date', 'Please enter date in DD-MM-YYYY or YYYY-MM-DD')
            return
        category = self.category_entry.get().strip() or 'Misc'
        amount_s = self.amount_entry.get().strip()
        try:
            amount = float(amount_s)
        except Exception:
            messagebox.showerror('Invalid Amount', 'Amount must be a number')
            return
        note = self.note_entry.get().strip()
        expense = {'date': date, 'category': category, 'amount': amount, 'note': note}
        self.expenses.append(expense)
        save_expenses(self.expenses)
        self.refresh_table()
        self.update_dashboard()
        self.clear_inputs()
        # budget warning
        if self.budget is not None:
            total = sum(float(e.get('amount',0)) for e in self.expenses if is_in_month(e.get('date')))
            if total > self.budget:
                messagebox.showwarning('Budget Exceeded', f'This month total {total} exceeded budget {self.budget}')

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('No selection', 'Select a row to edit')
            return
        item = sel[0]
        vals = self.tree.item(item, 'values')
        # find corresponding expense index (approx match)
        idx = self._find_expense_index_by_values(vals)
        if idx is None:
            messagebox.showerror('Error', 'Could not find expense record')
            return
        # open edit dialog
        self._open_edit_window(idx)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('No selection', 'Select a row to delete')
            return
        if not messagebox.askyesno('Confirm', 'Delete selected expense?'):
            return
        item = sel[0]
        vals = self.tree.item(item, 'values')
        idx = self._find_expense_index_by_values(vals)
        if idx is None:
            messagebox.showerror('Error', 'Could not find expense record')
            return
        del self.expenses[idx]
        save_expenses(self.expenses)
        self.refresh_table()
        self.update_dashboard()

    def _find_expense_index_by_values(self, vals):
        # vals: date, category, amount, note
        for i, e in enumerate(self.expenses):
            if (str(e.get('date','')) == str(vals[0]) and
                str(e.get('category','')) == str(vals[1]) and
                str(e.get('amount','')) == str(vals[2]) and
                str(e.get('note','')) == str(vals[3])):
                return i
        # fallback: try matching by date+amount
        for i, e in enumerate(self.expenses):
            if (str(e.get('date','')) == str(vals[0]) and str(e.get('amount','')) == str(vals[2])):
                return i
        return None

    def _open_edit_window(self, idx):
        e = self.expenses[idx]
        win = tb.Toplevel(self.root)
        win.title('Edit Expense')
        win.geometry('360x220')
        tb.Label(win, text='Date (DD-MM-YYYY)').pack(anchor='w', padx=8, pady=2)
        date_e = tb.Entry(win); date_e.pack(fill='x', padx=8); date_e.insert(0, e.get('date',''))
        tb.Label(win, text='Category').pack(anchor='w', padx=8, pady=2)
        cat_e = tb.Entry(win); cat_e.pack(fill='x', padx=8); cat_e.insert(0, e.get('category',''))
        tb.Label(win, text='Amount').pack(anchor='w', padx=8, pady=2)
        amt_e = tb.Entry(win); amt_e.pack(fill='x', padx=8); amt_e.insert(0, str(e.get('amount','')))
        tb.Label(win, text='Note').pack(anchor='w', padx=8, pady=2)
        note_e = tb.Entry(win); note_e.pack(fill='x', padx=8); note_e.insert(0, e.get('note',''))

        def save_edit():
            date = date_e.get().strip()
            if parse_date(date) is None:
                messagebox.showerror('Invalid Date', 'Use DD-MM-YYYY or YYYY-MM-DD')
                return
            cat = cat_e.get().strip() or 'Misc'
            try:
                amt = float(amt_e.get().strip())
            except Exception:
                messagebox.showerror('Invalid Amount', 'Amount must be a number')
                return
            note = note_e.get().strip()
            self.expenses[idx] = {'date': date, 'category': cat, 'amount': amt, 'note': note}
            save_expenses(self.expenses)
            self.refresh_table()
            self.update_dashboard()
            win.destroy()
        tb.Button(win, text='Save', bootstyle=SUCCESS, command=save_edit).pack(pady=8)

    def clear_inputs(self):
        self.date_entry.delete(0,'end')
        self.category_entry.delete(0,'end')
        self.amount_entry.delete(0,'end')
        self.note_entry.delete(0,'end')

    # ---------------------- Filters/Search ----------------------
    def refresh_table(self, filtered=None):
        for r in self.tree.get_children():
            self.tree.delete(r)
        data = filtered if filtered is not None else self.expenses
        for e in data:
            self.tree.insert('', 'end', values=(e.get('date',''), e.get('category',''), str(e.get('amount','')), e.get('note','')))

    def apply_filters(self):
        from_s = self.from_entry.get().strip()
        to_s = self.to_entry.get().strip()
        cat = self.cat_filter.get().strip().lower()
        filtered = []
        for e in self.expenses:
            ok = True
            if cat and cat not in str(e.get('category','')).lower(): ok = False
            if from_s:
                d = parse_date(e.get('date',''))
                dfrom = parse_date(from_s)
                if d is None or dfrom is None or d < dfrom: ok = False
            if to_s:
                d = parse_date(e.get('date',''))
                dto = parse_date(to_s)
                if d is None or dto is None or d > dto: ok = False
            if ok: filtered.append(e)
        self.refresh_table(filtered)

    def search(self):
        q = self.search_var.get().strip().lower()
        if not q:
            self.refresh_table()
            return
        out = []
        for e in self.expenses:
            if q in str(e.get('date','')).lower() or q in str(e.get('category','')).lower() or q in str(e.get('note','')).lower() or q in str(e.get('amount','')):
                out.append(e)
        self.refresh_table(out)

    def reset_filters(self):
        self.from_entry.delete(0,'end')
        self.to_entry.delete(0,'end')
        self.cat_filter.delete(0,'end')
        self.search_var.set('')
        self.refresh_table()

    # ---------------------- Dashboard & Charts ----------------------
    def update_dashboard(self):
        total_all = sum(float(e.get('amount',0)) for e in self.expenses)
        total_month = sum(float(e.get('amount',0)) for e in self.expenses if is_in_month(e.get('date')))
        total_today = sum(float(e.get('amount',0)) for e in self.expenses if is_today(e.get('date')))
        self.today_var.set(str(total_today))
        self.month_var.set(str(total_month))
        self.all_var.set(str(total_all))

    def show_pie(self):
        # Pie chart of categories
        cat_sum = {}
        for e in self.expenses:
            c = e.get('category','Misc')
            cat_sum[c] = cat_sum.get(c,0) + float(e.get('amount',0))
        if not cat_sum:
            messagebox.showinfo('No Data', 'No expenses to show')
            return
        fig = Figure(figsize=(5,4), dpi=100)
        ax = fig.add_subplot(111)
        labels = list(cat_sum.keys())
        sizes = list(cat_sum.values())
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        ax.set_title('Spending by Category')
        self._show_figure_window(fig, 'Category Pie Chart')

    def show_monthly_bars(self):
        # Aggregate by month-year
        by_month = {}
        for e in self.expenses:
            d = parse_date(e.get('date'))
            if not d: continue
            key = f"{d.year}-{d.month:02d}"
            by_month[key] = by_month.get(key,0) + float(e.get('amount',0))
        if not by_month:
            messagebox.showinfo('No Data', 'No expenses to show')
            return
        keys = sorted(by_month.keys())
        vals = [by_month[k] for k in keys]
        fig = Figure(figsize=(6,4), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(keys, vals)
        ax.set_title('Monthly Expenses')
        ax.set_xticklabels(keys, rotation=45, ha='right')
        self._show_figure_window(fig, 'Monthly Bars')

    def _show_figure_window(self, fig, title='Chart'):
        w = tb.Toplevel(self.root)
        w.title(title)
        canvas = FigureCanvasTkAgg(fig, master=w)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ---------------------- Data & Export UI ----------------------
    def export_csv_ui(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files','*.csv')])
        if not path: return
        try:
            export_csv(self.expenses, path)
            messagebox.showinfo('Exported', f'CSV saved to {path}')
        except Exception as ex:
            messagebox.showerror('Error', str(ex))

    def export_pdf_ui(self):
        path = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF files','*.pdf')])
        if not path: return
        try:
            export_pdf_summary(self.expenses, path)
            messagebox.showinfo('Exported', f'PDF saved to {path}')
        except Exception as ex:
            messagebox.showerror('Error', str(ex))

    def backup_ui(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files','*.json')])
        if not path: return
        try:
            backup_json(path)
            messagebox.showinfo('Backup', f'Backup saved to {path}')
        except Exception as ex:
            messagebox.showerror('Error', str(ex))

    def restore_ui(self):
        path = filedialog.askopenfilename(filetypes=[('JSON files','*.json')])
        if not path: return
        try:
            data = restore_json(path)
            self.expenses = data
            self.refresh_table()
            self.update_dashboard()
            messagebox.showinfo('Restored', 'Data restored from JSON')
        except Exception as ex:
            messagebox.showerror('Error', str(ex))

    # ---------------------- Budget ----------------------
    def set_budget(self):
        s = self.budget_entry.get().strip()
        try:
            val = float(s)
            self.budget = val
            messagebox.showinfo('Budget Set', f'Monthly budget set to {val}')
        except Exception:
            messagebox.showerror('Invalid', 'Budget must be a number')

    def clear_budget(self):
        self.budget = None
        self.budget_entry.delete(0,'end')
        messagebox.showinfo('Budget Cleared', 'Monthly budget cleared')

    # ---------------------- Theme ----------------------
    def change_theme(self, name):
        try:
            self.style.theme_use(name)
            self.current_theme = name
        except Exception:
            # fallback: recreate window is costly; show message
            messagebox.showinfo('Theme', 'Theme change may not be supported on this platform')

# ---------------------- Run App ----------------------

if __name__ == '__main__':
    app_root = tb.Window(themename=DEFAULT_THEME)
    app = ExpenseApp(app_root)
    app_root.mainloop()
