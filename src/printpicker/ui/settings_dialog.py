"""Settings dialog: where selections are stored and the print price list."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from printpicker.core.pricing import DEFAULT_PRICE_LIST, FixedCost, PriceList, PriceTier
from printpicker.ui.money import format_money
from printpicker.ui.settings import AppSettings, default_base_dir

EXAMPLE_COUNTS = (10, 50, 100, 250)


def parse_decimal(text: str) -> Decimal:
    """Accept both "0,35" and "0.35"; an optional currency symbol is ignored."""
    cleaned = text.strip().replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(text) from exc


def _table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setMinimumHeight(150)
    return table


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumWidth(560)

        self.base_dir_edit = QLineEdit(str(settings.base_dir))
        browse = QPushButton(self.tr("Browse…"))
        browse.clicked.connect(self._browse)
        reset = QPushButton(self.tr("Default"))
        reset.clicked.connect(lambda: self.base_dir_edit.setText(str(default_base_dir())))
        row = QHBoxLayout()
        row.addWidget(self.base_dir_edit, 1)
        row.addWidget(browse)
        row.addWidget(reset)
        hint = QLabel(self.tr("New selections are created here. Existing ones are not moved."))
        hint.setEnabled(False)

        form = QFormLayout()
        form.addRow(self.tr("Selections folder:"), row)
        form.addRow("", hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.body = QVBoxLayout(self)
        self.body.addLayout(form)
        self.body.addWidget(self._build_prices())
        self.body.addWidget(buttons)
        self.load_price_list(settings.price_list)

    # Price list ---------------------------------------------------------------------------

    def _build_prices(self) -> QWidget:
        box = QGroupBox(self.tr("Print price list (for the cost estimate)"))
        self.price_name = QLineEdit()
        self.tiers_table = _table([self.tr("From photos"), self.tr("Price per photo")])
        self.fixed_table = _table([self.tr("Fixed cost"), self.tr("Amount")])
        self.tiers_table.itemChanged.connect(self._update_examples)
        self.fixed_table.itemChanged.connect(self._update_examples)
        self.examples = QLabel()
        self.examples.setWordWrap(True)

        def buttons_for(table: QTableWidget, defaults: tuple[str, str]) -> QHBoxLayout:
            add = QPushButton(self.tr("Add"))
            add.clicked.connect(lambda: self._add_row(table, *defaults))
            remove = QPushButton(self.tr("Remove"))
            remove.clicked.connect(lambda: self._remove_rows(table))
            row = QHBoxLayout()
            row.addWidget(add)
            row.addWidget(remove)
            row.addStretch()
            return row

        restore = QPushButton(self.tr("Restore PhotoSì 10×15 prices"))
        restore.clicked.connect(lambda: self.load_price_list(DEFAULT_PRICE_LIST))

        tiers = QVBoxLayout()
        tiers.addWidget(self.tiers_table)
        tiers.addLayout(buttons_for(self.tiers_table, ("", "")))
        fixed = QVBoxLayout()
        fixed.addWidget(self.fixed_table)
        fixed.addLayout(buttons_for(self.fixed_table, (self.tr("Shipping"), "0,00")))
        tables = QHBoxLayout()
        tables.addLayout(tiers)
        tables.addLayout(fixed)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(self.tr("Name:")))
        name_row.addWidget(self.price_name, 1)
        name_row.addWidget(restore)

        hint = QLabel(
            self.tr(
                "The price of the tier reached applies to all the photos "
                "(e.g. 120 photos all at the “from 100” price)."
            )
        )
        hint.setWordWrap(True)
        hint.setEnabled(False)

        layout = QVBoxLayout(box)
        layout.addLayout(name_row)
        layout.addLayout(tables)
        layout.addWidget(hint)
        layout.addWidget(self.examples)
        return box

    def _add_row(self, table: QTableWidget, first: str, second: str) -> None:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(first))
        table.setItem(row, 1, QTableWidgetItem(second))
        table.setCurrentCell(row, 0)
        table.editItem(table.item(row, 0))

    def _remove_rows(self, table: QTableWidget) -> None:
        for row in sorted({i.row() for i in table.selectedIndexes()}, reverse=True):
            table.removeRow(row)
        self._update_examples()

    def load_price_list(self, price_list: PriceList) -> None:
        self.price_name.setText(price_list.name)
        self.currency = price_list.currency
        for table in (self.tiers_table, self.fixed_table):
            table.blockSignals(True)
            table.setRowCount(0)
        for tier in price_list.tiers:
            row = self.tiers_table.rowCount()
            self.tiers_table.insertRow(row)
            self.tiers_table.setItem(row, 0, QTableWidgetItem(str(tier.min_quantity)))
            self.tiers_table.setItem(row, 1, QTableWidgetItem(self._decimal_text(tier.unit_price)))
        for cost in price_list.fixed_costs:
            row = self.fixed_table.rowCount()
            self.fixed_table.insertRow(row)
            self.fixed_table.setItem(row, 0, QTableWidgetItem(cost.name))
            self.fixed_table.setItem(row, 1, QTableWidgetItem(self._decimal_text(cost.amount)))
        for table in (self.tiers_table, self.fixed_table):
            table.blockSignals(False)
        self._update_examples()

    def _decimal_text(self, value: Decimal) -> str:
        return self.locale().toString(float(value), "f", 2)

    def price_list(self) -> PriceList:
        """The edited price list; raises ValueError with a readable message if invalid."""

        def cell(table: QTableWidget, row: int, col: int) -> str:
            item = table.item(row, col)
            return item.text().strip() if item else ""

        tiers = []
        for row in range(self.tiers_table.rowCount()):
            quantity, price = cell(self.tiers_table, row, 0), cell(self.tiers_table, row, 1)
            if not quantity and not price:
                continue
            try:
                tiers.append(PriceTier(int(quantity), parse_decimal(price)))
            except ValueError as exc:
                raise ValueError(
                    self.tr("Row %1 of the tiers is not valid.").replace("%1", str(row + 1))
                ) from exc
        costs = []
        for row in range(self.fixed_table.rowCount()):
            name, amount = cell(self.fixed_table, row, 0), cell(self.fixed_table, row, 1)
            if not name and not amount:
                continue
            try:
                costs.append(FixedCost(name or self.tr("Fixed cost"), parse_decimal(amount)))
            except ValueError as exc:
                raise ValueError(
                    self.tr("Row %1 of the fixed costs is not valid.").replace("%1", str(row + 1))
                ) from exc
        try:
            return PriceList(
                self.price_name.text().strip() or self.tr("Price list"),
                tuple(tiers),
                tuple(costs),
                self.currency,
            )
        except ValueError as exc:
            raise ValueError(
                self.tr(
                    "The tiers must start from 1 photo, with different quantities and "
                    "non-negative prices."
                )
            ) from exc

    def _update_examples(self, *_args) -> None:
        try:
            price_list = self.price_list()
        except ValueError as exc:
            self.examples.setText(f"<span style='color:#c33'>{exc}</span>")
            return
        parts = [
            self.tr("%1 photos ≈ %2")
            .replace("%1", str(n))
            .replace("%2", format_money(price_list.estimate(n).total, price_list.currency))
            for n in EXAMPLE_COUNTS
        ]
        self.examples.setText(self.tr("Examples: ") + " · ".join(parts))

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Selections folder"), self.base_dir_edit.text()
        )
        if folder:
            self.base_dir_edit.setText(folder)

    def accept(self) -> None:
        try:
            price_list = self.price_list()
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Price list"), str(exc))
            return
        self.settings.price_list = price_list
        text = self.base_dir_edit.text().strip()
        if text:
            self.settings.base_dir = Path(text)
        super().accept()
