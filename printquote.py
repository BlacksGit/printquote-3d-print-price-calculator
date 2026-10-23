import json, os, csv, html, datetime, webbrowser, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import core

CFG = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'printquote.json')
LABELS = [('spool_price', 'Filament price per kg ($)'), ('waste', 'Waste factor (1.05 = 5%)'),
          ('watts', 'Printer power (watts)'), ('kwh_price', 'Electricity ($ per kWh)'),
          ('machine_hour', 'Machine wear ($ per hour)'), ('labor_minutes', 'Labor per print (minutes)'),
          ('labor_rate', 'Labor rate ($ per hour)'), ('failure_pct', 'Failed print allowance (%)'),
          ('markup_pct', 'Markup (%)'), ('fee_pct', 'Marketplace fee (%)'), ('fee_flat', 'Fee per order ($)')]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('PrintQuote - 3D print price calculator')
        self.geometry('900x560')
        self.cfg = dict(core.DEFAULTS)
        try:
            self.cfg.update(json.load(open(CFG)))
        except Exception:
            pass
        self.vars = {}
        side = ttk.Frame(self, padding=8)
        side.pack(side='left', fill='y')
        for i, (k, label) in enumerate(LABELS):
            ttk.Label(side, text=label).grid(row=i, column=0, sticky='w', pady=2)
            v = tk.StringVar(value=str(self.cfg[k]))
            v.trace_add('write', lambda *a: self.refresh())
            ttk.Entry(side, textvariable=v, width=8).grid(row=i, column=1, padx=4)
            self.vars[k] = v
        ttk.Label(side, text='Customer / note').grid(row=len(LABELS), column=0, sticky='w', pady=(10, 2))
        self.customer = tk.StringVar()
        ttk.Entry(side, textvariable=self.customer, width=18).grid(row=len(LABELS), column=1, columnspan=1)
        main = ttk.Frame(self, padding=8)
        main.pack(side='left', fill='both', expand=True)
        bar = ttk.Frame(main)
        bar.pack(fill='x')
        for text, cmd in [('Add G-code files', self.add), ('Remove selected', self.remove), ('Set quantity', self.qty),
                          ('Export CSV', self.export_csv), ('Open quote page', self.export_html)]:
            ttk.Button(bar, text=text, command=cmd).pack(side='left', padx=2)
        cols = ('file', 'grams', 'time', 'qty', 'cost', 'price', 'total')
        self.tree = ttk.Treeview(main, columns=cols, show='headings')
        for c, w in zip(cols, (240, 60, 70, 40, 70, 70, 80)):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor='w' if c == 'file' else 'e')
        self.tree.pack(fill='both', expand=True, pady=6)
        self.total = ttk.Label(main, text='', font=('Segoe UI', 11, 'bold'))
        self.total.pack(anchor='e')
        ttk.Label(main, text='Reads filament weight and print time from slicer G-code comments (tested: OrcaSlicer).').pack(anchor='w')
        self.items = []
        self.protocol('WM_DELETE_WINDOW', self.close)

    def conf(self):
        c = {}
        for k, v in self.vars.items():
            try:
                c[k] = float(v.get())
            except ValueError:
                c[k] = self.cfg[k]
        return c

    def add(self):
        for p in filedialog.askopenfilenames(filetypes=[('G-code', '*.gcode *.gco *.g *.bgcode'), ('All', '*.*')]):
            try:
                g, s, mm = core.read_gcode(p)
                if g is None and mm:
                    g = core.grams_from_mm(mm)
                if g is None or s is None:
                    raise ValueError('no weight or time found in file')
                self.items.append({'file': os.path.basename(p), 'grams': g, 'secs': s, 'qty': 1})
            except Exception as e:
                messagebox.showwarning('Skipped', f'{os.path.basename(p)}: {e}')
        self.refresh()

    def remove(self):
        for i in sorted((self.tree.index(s) for s in self.tree.selection()), reverse=True):
            del self.items[i]
        self.refresh()

    def qty(self):
        sel = self.tree.selection()
        if not sel:
            return
        win = tk.Toplevel(self)
        win.title('Quantity')
        v = tk.StringVar(value='1')
        ttk.Entry(win, textvariable=v, width=8).pack(padx=10, pady=8)
        def ok():
            try:
                n = max(1, int(v.get()))
            except ValueError:
                n = 1
            for s in sel:
                self.items[self.tree.index(s)]['qty'] = n
            win.destroy()
            self.refresh()
        ttk.Button(win, text='OK', command=ok).pack(pady=(0, 8))

    def rows(self):
        c = self.conf()
        out = []
        for it in self.items:
            q = core.quote(it['grams'], it['secs'], c)
            out.append((it, q, q['price'] * it['qty']))
        return out

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        tot = 0
        for it, q, line in self.rows():
            h, m = divmod(it['secs'] // 60, 60)
            self.tree.insert('', 'end', values=(it['file'], f"{it['grams']:.1f}", f'{h}h {m:02d}m', it['qty'],
                                                f"${q['cost']:.2f}", f"${q['price']:.2f}", f'${line:.2f}'))
            tot += line
        self.total.config(text=f'Total: ${tot:.2f}')

    def export_csv(self):
        p = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='quote.csv')
        if not p:
            return
        with open(p, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['file', 'grams', 'minutes', 'qty', 'filament', 'power', 'wear', 'labor', 'cost', 'price', 'line total'])
            for it, q, line in self.rows():
                w.writerow([it['file'], round(it['grams'], 1), it['secs'] // 60, it['qty']] +
                           [round(q[k], 2) for k in ('filament', 'power', 'wear', 'labor', 'cost', 'price')] + [round(line, 2)])

    def export_html(self):
        rows = self.rows()
        body = ''.join(f"<tr><td>{html.escape(it['file'])}</td><td>{it['qty']}</td><td>${q['price']:.2f}</td><td>${line:.2f}</td></tr>"
                       for it, q, line in rows)
        total = sum(r[2] for r in rows)
        page = (f"<html><body style='font-family:sans-serif;max-width:700px;margin:30px auto'><h2>Quote</h2>"
                f"<p>{html.escape(self.customer.get())}<br>{datetime.date.today()}</p>"
                f"<table border=1 cellpadding=6 style='border-collapse:collapse;width:100%'><tr><th>Item</th><th>Qty</th><th>Each</th><th>Total</th></tr>{body}</table>"
                f"<h3 style='text-align:right'>Total: ${total:.2f}</h3><p>Use your browser's Print, Save as PDF.</p></body></html>")
        p = os.path.join(tempfile.gettempdir(), 'printquote.html')
        open(p, 'w').write(page)
        webbrowser.open(p)

    def close(self):
        json.dump(self.conf(), open(CFG, 'w'))
        self.destroy()

if __name__ == '__main__':
    App().mainloop()
