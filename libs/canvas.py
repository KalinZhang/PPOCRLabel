# Copyright (c) <2015-Present> Tzutalin
# Copyright (C) 2013  MIT, Computer Science and Artificial Intelligence Laboratory. Bryan Russell, Antonio Torralba,
# William T. Freeman. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction, including without
# limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import copy

from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QPoint, QRectF
from PyQt5.QtGui import QPainter, QBrush, QColor, QPixmap, QFontDatabase
from PyQt5.QtWidgets import QWidget, QMenu, QApplication
from libs.shape import Shape
from libs.utils import distance

CURSOR_DEFAULT = Qt.ArrowCursor
CURSOR_POINT = Qt.PointingHandCursor
CURSOR_DRAW = Qt.CrossCursor
CURSOR_MOVE = Qt.ClosedHandCursor
CURSOR_GRAB = Qt.OpenHandCursor


class Canvas(QWidget):
    zoomRequest = pyqtSignal(int)
    scrollRequest = pyqtSignal(int, int)
    newShape = pyqtSignal()
    # selectionChanged = pyqtSignal(bool)
    selectionChanged = pyqtSignal(list)
    shapeMoved = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)

    CREATE, EDIT = list(range(2))
    _fill_drawing = False  # draw shadows

    epsilon = 5.0

    shape_move_index = None

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        # Initialise local state.
        self.mode = self.EDIT
        self.shapes = []
        self.shapesBackups = []
        self.current = None
        self.selectedShapes = []
        self.selectedShape = None  # save the selected shape here
        self.selectedShapesCopy = []
        self.drawingLineColor = QColor(0, 0, 255)
        self.drawingRectColor = QColor(0, 0, 255)
        self.line = Shape(line_color=self.drawingLineColor)
        self.prevPoint = QPointF()
        self.offsets = QPointF(), QPointF()
        self.scale = 1.0
        self.pixmap = QPixmap()
        self.visible = {}
        self._hideBackround = False
        self.hideBackround = False
        self.hShape = None
        self.hVertex = None
        self._painter = QPainter()
        self._cursor = CURSOR_DEFAULT
        # Menus:
        self.menu = QMenu()
        deleteAction = self.menu.addAction("删除")
        deleteAction.triggered.connect(self.deleteSelected)
        # 设置菜单样式
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #F0F0F0;
                border: 1px solid #CCC;
            }
            QMenu::item {
                padding: 5px 25px 5px 25px;
            }
            QMenu::item:selected {
                background-color: #0078D7;
                color: white;
            }
        """)
        # Set widget options.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)
        self.verified = False
        self.drawSquare = False
        self.fourpoint = True  # ADD
        self.pointnum = 0
        self.movingShape = False
        self.selectCountShape = False

        # initialisation for panning
        self.pan_initial_pos = QPoint()

        # lockedshapes related
        self.lockedShapes = []
        self.isInTheSameImage = False

    def setDrawingColor(self, qColor):
        self.drawingLineColor = qColor
        self.drawingRectColor = qColor

    def enterEvent(self, ev):
        self.overrideCursor(self._cursor)

    def leaveEvent(self, ev):
        self.restoreCursor()

    def focusOutEvent(self, ev):
        self.restoreCursor()

    def isVisible(self, shape):
        return self.visible.get(shape, True)

    def drawing(self):
        """
        返回是否处于绘制模式
        """
        return self.mode == self.CREATE

    def editing(self):
        """
        返回是否处于编辑模式
        """
        return self.mode == self.EDIT

    def setEditing(self, value=True):
        print(f"Canvas: setEditing called with value={value}")
        self.mode = self.EDIT if value else self.CREATE
        if not value:  # 退出编辑模式
            if self.current:
                print("Canvas: Clearing current shape in setEditing")
                self.current = None
                self.drawingPolygon.emit(False)
                self.update()
        self.prevPoint = QPointF()
        self.repaint()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
        self.hVertex = self.hShape = None

    def selectedVertex(self):
        return self.hVertex is not None

    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""
        pos = self.transformPos(ev.pos())

        # Update coordinates in status bar if image is opened
        window = self.parent().window()
        if window.filePath is not None:
            self.parent().window().labelCoordinates.setText(
                "X: %d; Y: %d" % (pos.x(), pos.y())
            )

        # Polygon drawing.
        if self.drawing():
            self.overrideCursor(CURSOR_DRAW)  # ?
            if self.current:
                # Display annotation width and height while drawing
                currentWidth = abs(self.current[0].x() - pos.x())
                currentHeight = abs(self.current[0].y() - pos.y())
                self.parent().window().labelCoordinates.setText(
                    "Width: %d, Height: %d / X: %d; Y: %d"
                    % (currentWidth, currentHeight, pos.x(), pos.y())
                )

                color = self.drawingLineColor
                if self.outOfPixmap(pos):
                    # Don't allow the user to draw outside the pixmap.
                    # Clip the coordinates to 0 or max,
                    # if they are outside the range [0, max]
                    size = self.pixmap.size()
                    clipped_x = min(max(0, pos.x()), size.width())
                    clipped_y = min(max(0, pos.y()), size.height())
                    pos = QPointF(clipped_x, clipped_y)

                elif len(self.current) > 1 and self.closeEnough(pos, self.current[0]):
                    # Attract line to starting point and colorise to alert the
                    # user:
                    pos = self.current[0]
                    color = self.current.line_color
                    self.overrideCursor(CURSOR_POINT)
                    self.current.highlightVertex(0, Shape.NEAR_VERTEX)

                if self.drawSquare:
                    self.line.points = [self.current[0], pos]
                    self.line.close()

                elif self.fourpoint:
                    self.line[0] = self.current[-1]
                    self.line[1] = pos

                else:
                    self.line[1] = pos  # pos is the mouse's current position

                self.line.line_color = color
                self.prevPoint = QPointF()  # ？
                self.current.highlightClear()
            else:
                self.prevPoint = pos
            self.repaint()
            return

        # Polygon copy moving.
        if Qt.RightButton & ev.buttons():
            if self.selectedShapesCopy and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShape(self.selectedShapesCopy, pos)
                self.repaint()
            elif self.selectedShapes:
                self.selectedShapesCopy = [s.copy() for s in self.selectedShapes]
                self.repaint()
            return

        # Polygon/Vertex moving.
        if Qt.LeftButton & ev.buttons():
            if self.selectedVertex():
                self.boundedMoveVertex(pos)
                self.shapeMoved.emit()
                self.repaint()
                self.movingShape = True
            elif self.selectedShapes and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShape(self.selectedShapes, pos)
                self.shapeMoved.emit()
                self.repaint()
                self.movingShape = True
            else:
                # pan
                delta_x = pos.x() - self.pan_initial_pos.x()
                delta_y = pos.y() - self.pan_initial_pos.y()
                self.scrollRequest.emit(delta_x, Qt.Horizontal)
                self.scrollRequest.emit(delta_y, Qt.Vertical)
                self.update()
            return

        # Just hovering over the canvas, 2 posibilities:
        # - Highlight shapes
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
            # Look for a nearby vertex to highlight. If that fails,
            # check if we happen to be inside a shape.
            index = shape.nearestVertex(pos, self.epsilon)
            if index is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = index, shape
                shape.highlightVertex(index, shape.MOVE_VERTEX)
                self.overrideCursor(CURSOR_POINT)
                self.update()
                break
            else:
                for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
                    if shape.containsPoint(pos):
                        if self.selectedVertex():
                            self.hShape.highlightClear()
                        self.hVertex, self.hShape = None, shape
                        self.overrideCursor(CURSOR_GRAB)
                        self.update()
                        break
                else:  # Nothing found, clear highlights, reset state.
                    if self.hShape:
                        self.hShape.highlightClear()
                        self.update()
                    self.hVertex, self.hShape = None, None
                    self.overrideCursor(CURSOR_DEFAULT)

    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.pos())
        if ev.button() == Qt.LeftButton:
            if self.drawing():
                # self.handleDrawing(pos) # OLD
                if self.current:
                    if self.fourpoint:  # ADD IF
                        # Add point to existing shape.
                        # print('Adding points in mousePressEvent is ', self.line[1])
                        self.current.addPoint(self.line[1])
                        self.line[0] = self.current[-1]
                        if self.current.isClosed():
                            # print('1111')
                            self.finalise()
                    elif self.drawSquare:
                        assert len(self.current.points) == 1
                        self.current.points = self.line.points
                        self.finalise()
                elif not self.outOfPixmap(pos):
                    # Create new shape.
                    self.current = Shape()
                    self.current.addPoint(pos)
                    self.line.points = [pos, pos]
                    self.setHiding()
                    self.drawingPolygon.emit(True)
                    self.update()

            else:
                group_mode = int(ev.modifiers()) == Qt.ControlModifier
                self.selectShapePoint(pos, multiple_selection_mode=group_mode)
                self.prevPoint = pos
                self.pan_initial_pos = pos

        elif ev.button() == Qt.RightButton and self.editing():
            group_mode = int(ev.modifiers()) == Qt.ControlModifier
            self.selectShapePoint(pos, multiple_selection_mode=group_mode)
            self.prevPoint = pos
        self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.RightButton:
            if self.selectedShapes:  # 只在有选中形状时显示右键菜单
                self.menu.exec_(self.mapToGlobal(ev.pos()))
        
        elif ev.button() == Qt.LeftButton:
            if self.selectedShapes and self.shapesBackups:
                # 检查移动的形状
                try:
                    index = self.shapes.index(self.selectedShape)
                    if len(self.shapesBackups[-1]) > index:
                        if self.shapesBackups[-1][index].points != self.shapes[index].points:
                            self.storeShapes()
                            self.shapeMoved.emit()
                except (IndexError, ValueError):
                    pass

            if self.drawing():
                if self.current:
                    try:
                        if self.fourpoint:
                            # 处理四点模式
                            self.current.close()
                            self.finalise()
                        else:
                            # 处理其他模式
                            self.handleDrawing(self.transformPos(ev.pos()))
                    except:
                        # 如果在创建时发生错误，确保清理
                        self.current = None
                        self.drawingPolygon.emit(False)
                        self.update()
                else:
                    self.drawingPolygon.emit(False)
                    self.update()
            else:
                if self.selectedVertex():
                    self.overrideCursor(CURSOR_POINT)
                elif self.selectedShapes:
                    self.overrideCursor(CURSOR_GRAB)
                else:
                    self.restoreCursor()
                
            self.movingShape = False

    def endMove(self, copy=False):
        assert self.selectedShapes and self.selectedShapesCopy
        assert len(self.selectedShapesCopy) == len(self.selectedShapes)
        if copy:
            for i, shape in enumerate(self.selectedShapesCopy):
                shape.idx = len(self.shapes)  # add current box index
                self.shapes.append(shape)
                self.selectedShapes[i].selected = False
                self.selectedShapes[i] = shape
        else:
            for i, shape in enumerate(self.selectedShapesCopy):
                self.selectedShapes[i].points = shape.points
        self.selectedShapesCopy = []
        self.repaint()
        self.storeShapes()
        return True

    def hideBackroundShapes(self, value):
        self.hideBackround = value
        if self.selectedShapes:
            # Only hide other shapes if there is a current selection.
            # Otherwise the user will not be able to select a shape.
            self.setHiding(True)
            self.repaint()

    def handleDrawing(self, pos):
        """Handle drawing of shapes"""
        if self.current and self.current.reachMaxPoints() is False:
            if self.fourpoint:
                # 四点模式的处理
                initPos = pos
                self.current.addPoint(initPos)
                if len(self.current.points) == 4:
                    self.finalise()
            else:
                # 其他模式的处理
                initPos = self.current[0]
                minX = initPos.x()
                minY = initPos.y()
                targetPos = pos
                maxX = targetPos.x()
                maxY = targetPos.y()
                self.current.addPoint(QPointF(maxX, minY))
                self.current.addPoint(targetPos)
                self.current.addPoint(QPointF(minX, maxY))
                self.finalise()
        elif not self.outOfPixmap(pos):
            # 创建新的形状
            self.current = Shape()
            self.current.addPoint(pos)
            self.line.points = [pos, pos]
            self.setHiding()
            self.drawingPolygon.emit(True)
            self.update()

    def setHiding(self, enable=True):
        self._hideBackround = self.hideBackround if enable else False

    def canCloseShape(self):
        return self.drawing() and self.current and len(self.current) > 2

    def mouseDoubleClickEvent(self, ev):
        # We need at least 4 points here, since the mousePress handler
        # adds an extra one before this handler is called.
        if self.canCloseShape() and len(self.current) > 3:
            if not self.fourpoint:
                self.current.popPoint()
            self.finalise()

    def selectShapes(self, shapes):
        for s in shapes:
            s.seleted = True
        self.setHiding()
        self.selectionChanged.emit(shapes)
        self.update()

    def selectShapePoint(self, point, multiple_selection_mode):
        """Select the first shape created which contains this point."""
        if self.selectedVertex():  # A vertex is marked for selection.
            index, shape = self.hVertex, self.hShape
            shape.highlightVertex(index, shape.MOVE_VERTEX)
            return self.hVertex
        else:
            for shape in reversed(self.shapes):
                if self.isVisible(shape) and shape.containsPoint(point):
                    self.calculateOffsets(shape, point)
                    self.setHiding()
                    if multiple_selection_mode:
                        if shape not in self.selectedShapes:  # list
                            self.selectionChanged.emit(self.selectedShapes + [shape])
                    else:
                        self.selectionChanged.emit([shape])
                    return
        self.deSelectShape()

    def calculateOffsets(self, shape, point):
        rect = shape.boundingRect()
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        x2 = (rect.x() + rect.width()) - point.x()
        y2 = (rect.y() + rect.height()) - point.y()
        self.offsets = QPointF(x1, y1), QPointF(x2, y2)

    def snapPointToCanvas(self, x, y):
        """
        Moves a point x,y to within the boundaries of the canvas.
        :return: (x,y,snapped) where snapped is True if x or y were changed, False if not.
        """
        if x < 0 or x > self.pixmap.width() or y < 0 or y > self.pixmap.height():
            x = max(x, 0)
            y = max(y, 0)
            x = min(x, self.pixmap.width())
            y = min(y, self.pixmap.height())
            return x, y, True

        return x, y, False

    def boundedMoveVertex(self, pos):
        index, shape = self.hVertex, self.hShape
        point = shape[index]
        if self.outOfPixmap(pos):
            size = self.pixmap.size()
            clipped_x = min(max(0, pos.x()), size.width())
            clipped_y = min(max(0, pos.y()), size.height())
            pos = QPointF(clipped_x, clipped_y)

        if self.drawSquare:
            opposite_point_index = (index + 2) % 4
            opposite_point = shape[opposite_point_index]

            min_size = min(
                abs(pos.x() - opposite_point.x()), abs(pos.y() - opposite_point.y())
            )
            directionX = -1 if pos.x() - opposite_point.x() < 0 else 1
            directionY = -1 if pos.y() - opposite_point.y() < 0 else 1
            shiftPos = QPointF(
                opposite_point.x() + directionX * min_size - point.x(),
                opposite_point.y() + directionY * min_size - point.y(),
            )
        else:
            shiftPos = pos - point

        if [shape[0].x(), shape[0].y(), shape[2].x(), shape[2].y()] == [
            shape[3].x(),
            shape[1].y(),
            shape[1].x(),
            shape[3].y(),
        ]:
            shape.moveVertexBy(index, shiftPos)
            lindex = (index + 1) % 4
            rindex = (index + 3) % 4
            lshift = None
            rshift = None
            if index % 2 == 0:
                rshift = QPointF(shiftPos.x(), 0)
                lshift = QPointF(0, shiftPos.y())
            else:
                lshift = QPointF(shiftPos.x(), 0)
                rshift = QPointF(0, shiftPos.y())
            shape.moveVertexBy(rindex, rshift)
            shape.moveVertexBy(lindex, lshift)

        else:
            shape.moveVertexBy(index, shiftPos)

    def boundedMoveShape(self, shapes, pos):
        if type(shapes).__name__ != "list":
            shapes = [shapes]
        if self.outOfPixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QPointF(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QPointF(
                min(0, self.pixmap.width() - o2.x()),
                min(0, self.pixmap.height() - o2.y()),
            )
        # The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason. XXX
        # self.calculateOffsets(self.selectedShape, pos)
        dp = pos - self.prevPoint
        if dp:
            for shape in shapes:
                shape.moveBy(dp)
                shape.close()
            self.prevPoint = pos
            return True
        return False

    def deSelectShape(self):
        if self.selectedShapes:
            for shape in self.selectedShapes:
                shape.selected = False
            self.setHiding(False)
            self.selectionChanged.emit([])
            self.update()

    def deleteSelected(self):
        """
        删除选中的形状
        """
        print("Canvas: deleteSelected called")
        if self.selectedShapes:
            print(f"Canvas: Deleting {len(self.selectedShapes)} shapes")
            deleted = []
            for shape in self.selectedShapes:
                if shape in self.shapes:
                    self.shapes.remove(shape)
                    deleted.append(shape)
            self.selectedShapes = []
            self.update()
            print(f"Canvas: Successfully deleted {len(deleted)} shapes")
            return True
        print("Canvas: No shapes selected to delete")
        return False

    def updateShapeIndex(self):
        """
        更新形状的索引
        """
        for i, shape in enumerate(self.shapes):
            shape.idx = i
        self.update()

    def storeShapes(self):
        """
        存储形状的备份
        """
        shapesBackup = []
        shapesBackup = copy.deepcopy(self.shapes)
        if len(self.shapesBackups) >= 10:
            self.shapesBackups = self.shapesBackups[-9:]
        self.shapesBackups.append(shapesBackup)

    def copySelectedShape(self):
        if self.selectedShapes:
            self.selectedShapesCopy = [s.copy() for s in self.selectedShapes]
            self.boundedShiftShapes(self.selectedShapesCopy)
            self.endMove(copy=True)
        return self.selectedShapes

    def boundedShiftShapes(self, shapes):
        # Try to move in one direction, and if it fails in another.
        # Give up if both fail.
        for shape in shapes:
            point = shape[0]
            offset = QPointF(5.0, 5.0)
            self.calculateOffsets(shape, point)
            self.prevPoint = point
            if not self.boundedMoveShape(shape, point - offset):
                self.boundedMoveShape(shape, point + offset)

    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())

        p.drawPixmap(0, 0, self.pixmap)

        # 绘制所有形状
        for shape in self.shapes:
            if (shape.selected or not self._hideBackround) and \
               self.isVisible(shape):
                shape.paint(p)
                # 在框的上方绘制文本
                if shape.label:  # 如果有标签文本就显示
                    self.paintShapeLabel(p, shape)

        # 绘制当前正在创建的形状
        if self.current:
            self.current.paint(p)
            if self.current.label:
                self.paintShapeLabel(p, self.current)

        if self.selectedShapesCopy:
            for s in self.selectedShapesCopy:
                s.paint(p)

        # Paint rect
        if self.current is not None and len(self.line) == 2 and not self.fourpoint:
            # print('Drawing rect')
            leftTop = self.line[0]
            rightBottom = self.line[1]
            rectWidth = rightBottom.x() - leftTop.x()
            rectHeight = rightBottom.y() - leftTop.y()
            p.setPen(self.drawingRectColor)
            brush = QBrush(Qt.BDiagPattern)
            p.setBrush(brush)
            p.drawRect(
                int(leftTop.x()), int(leftTop.y()), int(rectWidth), int(rectHeight)
            )

        # ADD：
        if (
            self.fillDrawing()
            and self.fourpoint
            and self.current is not None
            and len(self.current.points) >= 2
        ):
            print("paint event")
            drawing_shape = self.current.copy()
            drawing_shape.addPoint(self.line[1])
            drawing_shape.fill = True
            drawing_shape.paint(p)

        if (
            self.drawing()
            and self.prevPoint is not None
            and not self.prevPoint.isNull()
            and not self.outOfPixmap(self.prevPoint)
        ):
            p.setPen(QColor(0, 0, 0))
            p.drawLine(
                int(self.prevPoint.x()),
                0,
                int(self.prevPoint.x()),
                int(self.pixmap.height()),
            )
            p.drawLine(
                0,
                int(self.prevPoint.y()),
                int(self.pixmap.width()),
                int(self.prevPoint.y()),
            )

        self.setAutoFillBackground(True)
        if self.verified:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(184, 239, 38, 128))
            self.setPalette(pal)
        else:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(232, 232, 232, 255))
            self.setPalette(pal)

        # adaptive BBOX label & index font size
        if self.pixmap:
            h, w = self.pixmap.size().height(), self.pixmap.size().width()
            fontszie = int(max(h, w) / 48)
            for s in self.shapes:
                s.fontsize = fontszie

        p.end()

    def fillDrawing(self):
        return self._fill_drawing

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical coordinates."""
        return point / self.scale - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def outOfPixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w and 0 <= p.y() <= h)

    def finalise(self):
        assert self.current
        if self.current.points[0] == self.current.points[-1]:
            # print('finalse')
            self.current = None
            self.drawingPolygon.emit(False)
            self.update()
            return

        self.current.close()
        self.current.idx = len(self.shapes)  # add current box index
        self.shapes.append(self.current)
        self.current = None
        self.setHiding(False)
        self.newShape.emit()
        self.update()

    def closeEnough(self, p1, p2):
        # d = distance(p1 - p2)
        # m = (p1-p2).manhattanLength()
        # print "d %.2f, m %d, %.2f" % (d, m, d - m)
        return distance(p1 - p2) < self.epsilon

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def wheelEvent(self, ev):
        qt_version = 4 if hasattr(ev, "delta") else 5
        if qt_version == 4:
            if ev.orientation() == Qt.Vertical:
                v_delta = ev.delta()
                h_delta = 0
            else:
                h_delta = ev.delta()
                v_delta = 0
        else:
            delta = ev.angleDelta()
            h_delta = delta.x()
            v_delta = delta.y()

        mods = ev.modifiers()
        if Qt.ControlModifier == int(mods) and v_delta:
            self.zoomRequest.emit(v_delta)
        else:
            v_delta and self.scrollRequest.emit(v_delta, Qt.Vertical)
            h_delta and self.scrollRequest.emit(h_delta, Qt.Horizontal)
        ev.accept()

    def keyPressEvent(self, ev):
        """
        处理按键事件
        """
        key = ev.key()
        
        if key == Qt.Key_Escape:
            print("Canvas: ESC key pressed")
            
            # 先退出绘制状态
            if self.mode == self.CREATE:  # 使用 mode 判断而不是调用 drawing()
                print("Canvas: Currently in drawing mode")
                # 清除当前正在绘制的形状
                if self.current:
                    print("Canvas: Clearing current shape")
                    self.current = None
                
                # 清除所有未确认的形状
                shapes_to_remove = []
                for shape in self.shapes:
                    if not hasattr(shape, 'confirmed') or not shape.confirmed:
                        shapes_to_remove.append(shape)
                
                if shapes_to_remove:
                    print(f"Canvas: Removing {len(shapes_to_remove)} unconfirmed shapes")
                    self.shapes = [s for s in self.shapes if s not in shapes_to_remove]
                
                # 退出绘制模式
                self.mode = self.EDIT
                self.drawingPolygon.emit(False)
                self.restoreCursor()
                self.update()
                print("Canvas: All shapes cleared and drawing cancelled")
                return
        
        elif key == Qt.Key_Return:
            self.overrideCursor(CURSOR_DEFAULT)
            if self.canCloseShape():
                self.finalise()
        elif key == Qt.Key_Left and self.selectedShapes:
            self.moveOnePixel("Left")
        elif key == Qt.Key_Right and self.selectedShapes:
            self.moveOnePixel("Right")
        elif key == Qt.Key_Up and self.selectedShapes:
            self.moveOnePixel("Up")
        elif key == Qt.Key_Down and self.selectedShapes:
            self.moveOnePixel("Down")

    def restoreShape(self):
        """
        恢复到上一个状态
        """
        if not self.shapesBackups:
            return
        shapes = self.shapesBackups[-1]
        self.shapes = shapes
        self.selectedShapes = []
        for shape in self.shapes:
            shape.selected = False
        self.update()

    def moveOnePixel(self, direction):
        # print(self.selectedShape.points)
        self.selectCount = len(self.selectedShapes)
        self.selectCountShape = True
        for i in range(len(self.selectedShapes)):
            self.selectedShape = self.selectedShapes[i]
            if direction == "Left" and not self.moveOutOfBound(QPointF(-1.0, 0)):
                # print("move Left one pixel")
                self.move_points(QPointF(-1.0, 0))
            elif direction == "Right" and not self.moveOutOfBound(QPointF(1.0, 0)):
                # print("move Right one pixel")
                self.move_points(QPointF(1.0, 0))
            elif direction == "Up" and not self.moveOutOfBound(QPointF(0, -1.0)):
                # print("move Up one pixel")
                self.move_points(QPointF(0, -1.0))
            elif direction == "Down" and not self.moveOutOfBound(QPointF(0, 1.0)):
                # print("move Down one pixel")
                self.move_points(QPointF(0, 1.0))
        shapesBackup = []
        shapesBackup = copy.deepcopy(self.shapes)
        self.shapesBackups.append(shapesBackup)
        self.shapeMoved.emit()
        self.repaint()

    def move_points(self, p: QPointF):
        if self.shape_move_index is None:
            self.selectedShape.points[0] += p
            self.selectedShape.points[1] += p
            self.selectedShape.points[2] += p
            self.selectedShape.points[3] += p
        else:
            self.selectedShape.points[self.shape_move_index] += p

    def moveOutOfBound(self, step):
        points = [p1 + p2 for p1, p2 in zip(self.selectedShape.points, [step] * 4)]
        return True in map(self.outOfPixmap, points)

    def setLastLabel(self, text):
        assert text
        if self.shapes:
            self.shapes[-1].label = text
            self.shapes[-1].paintLabel = True  # 确保标签会被绘制
            self.update()  # 触发重绘
            return self.shapes[-1]
        return None

    def undoLastLine(self):
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)

    def undoLastPoint(self):
        if not self.current or self.current.isClosed():
            return
        self.current.popPoint()
        if len(self.current) > 0:
            self.line[0] = self.current[-1]
        else:
            self.current = None
            self.drawingPolygon.emit(False)
        self.repaint()

    def resetAllLines(self):
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)
        self.current = None
        self.drawingPolygon.emit(False)
        self.update()

    def loadPixmap(self, pixmap):
        self.pixmap = pixmap
        self.shapes = []
        self.repaint()

    def loadShapes(self, shapes, replace=True):
        if replace:
            self.shapes = list(shapes)
        else:
            self.shapes.extend(shapes)
        self.current = None
        self.hShape = None
        self.hVertex = None
        # self.hEdge = None
        self.storeShapes()
        self.updateShapeIndex()
        self.repaint()

    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.repaint()

    def currentCursor(self):
        cursor = QApplication.overrideCursor()
        if cursor is not None:
            cursor = cursor.shape()
        return cursor

    def overrideCursor(self, cursor):
        self._cursor = cursor
        if self.currentCursor() is None:
            QApplication.setOverrideCursor(cursor)
        else:
            QApplication.changeOverrideCursor(cursor)

    def restoreCursor(self):
        QApplication.restoreOverrideCursor()

    def resetState(self):
        self.restoreCursor()
        self.pixmap = None
        self.update()
        self.shapesBackups = []

    def setDrawingShapeToSquare(self, status):
        self.drawSquare = status

    def paintShapeLabel(self, painter, shape):
        if shape.label is None:
            return

        # 计算文本位置（框的上方中心）
        points = shape.points
        xmin = min(p.x() for p in points)
        ymin = min(p.y() for p in points)
        xmax = max(p.x() for p in points)
        
        # 设置字体
        font = painter.font()
        font_families = [
            "Estrangelo Edessa",
            "Noto Sans Syriac",
            "East Syriac Adiabene",
            "Serto Jerusalem",
            "Microsoft Sans Serif",
            "Arial Unicode MS",
            "Arial"
        ]
        
        db = QFontDatabase()
        available_families = db.families()
        for family in font_families:
            if family in available_families:
                font.setFamily(family)
                break
            
        font.setPointSize(10)  # 调整字体大小
        painter.setFont(font)
        
        # 获取文本度量
        fm = painter.fontMetrics()
        text_width = fm.width(shape.label)
        text_height = fm.height()
        
        # 计算文本位置
        x = xmin + (xmax - xmin - text_width) / 2
        y = ymin - text_height - 5  # 将文本放在框上方，并留出5像素的间距
        
        # 绘制白色背景
        padding = 2
        bg_rect = QRectF(
            x - padding,
            y - padding,
            text_width + 2 * padding,
            text_height + 2 * padding
        )
        painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
        
        # 绘制文本
        painter.setPen(shape.line_color)
        painter.drawText(QPointF(x, y + text_height - fm.descent()), shape.label)

    def reset(self):
        """
        重置画布状态
        """
        self.restoreCursor()
        self.current = None
        self.drawingPolygon.emit(False)
        self.update()

    def cancelDrawing(self):
        """
        完全取消当前的绘制过程
        """
        if self.current:
            # 清除当前正在绘制的形状
            self.current = None
            self.drawingPolygon.emit(False)
            # 重置绘制状态
            self.drawing = False
            # 恢复默认光标
            self.restoreCursor()
            # 更新画布
            self.update()

    def isDrawing(self):
        """
        检查是否正在绘制
        """
        return self.drawing and self.current is not None
