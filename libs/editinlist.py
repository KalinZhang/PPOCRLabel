# !/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QListView


class EditInList(QListWidget):
    def __init__(self):
        super(EditInList, self).__init__()
        self.edited_item = None
        
        # 设置字体
        font = QFont()
        # 尝试使用支持叙利亚文的字体
        font_families = [
            "Estrangelo Edessa",
            "Noto Sans Syriac",
            "East Syriac Adiabene",
            "Serto Jerusalem",
            "Microsoft Sans Serif",
            "Arial Unicode MS",
            "Arial"
        ]
        
        # 修正字体检查方法
        db = QFontDatabase()
        available_families = db.families()
        for family in font_families:
            if family in available_families:
                font.setFamily(family)
                break
        
        font.setPointSize(12)
        self.setFont(font)
        
        # 设置文本方向为从右到左
        self.setLayoutDirection(Qt.RightToLeft)
        
        # 设置文本对齐方式
        self.setTextElideMode(Qt.ElideRight)
        
        # 设置选择模式
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # 设置视图模式
        self.setViewMode(QListView.ListMode)
        
        # 设置统一项目大小
        self.setUniformItemSizes(True)
        
        # 设置自动滚动
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def item_clicked(self, modelindex: QModelIndex):
        try:
            if self.edited_item is not None:
                self.closePersistentEditor(self.edited_item)
        except:
            self.edited_item = self.currentItem()

        self.edited_item = self.item(modelindex.row())
        self.openPersistentEditor(self.edited_item)
        self.editItem(self.edited_item)

    def mouseDoubleClickEvent(self, event):
        pass

    def leaveEvent(self, event):
        pass

    def addItem(self, item):
        """
        重写 addItem 方法，确保新添加的项目使用正确的字体和对齐方式
        """
        if isinstance(item, str):
            item = HashableQListWidgetItem(item)
            item.setFont(self.font())
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        else:
            item.setFont(self.font())
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        super(EditInList, self).addItem(item)
        return item  # 返回创建的项目，以便建立映射关系

    def keyPressEvent(self, event) -> None:
        # close edit
        if event.key() in [16777220, 16777221]:
            for i in range(self.count()):
                self.closePersistentEditor(self.item(i))
