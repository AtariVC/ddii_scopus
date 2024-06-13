from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QObject

class pyToggle(QCheckBox):
    def __init__(self,
                 width = 60,
                 bg_color = "#f8f8f8",
                 circle_color = "#DDD",
                 active_color = "#32c75a",
                 border_color = "#b9b9b9",
                 circle_active_color = "#f8f8f8",
                 animation_curve = QEasingCurve.Type.OutBounce,
                 ):
        QCheckBox.__init__(self)

        # Default parameters
        self.setFixedSize(width, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # color
        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color
        self._border_color = border_color
        self.circle_active_color = circle_active_color




        # Animation
        self._circle_position = 3
        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(animation_curve)
        self.animation.setDuration(500)

        # connect state change
        self.stateChanged.connect(self.start_transition)

    # Create new set and get property
    @property  # get
    def circle_position(self):
        return self._circle_position

    @circle_position.setter  # set
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def start_transition(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(self.width() - 26)
        else:
            self.animation.setEndValue(3)

        # start animation
        self.animation.start()
        print(f"Status: {self.isChecked()}")

    # set new hit area
    def hitButton(self, pos: QPoint) -> bool:
        return self.contentsRect().contains(pos)

    # draw new items
    def paintEvent(self, e) -> None:
        # Set paiter
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set as no pen
        p.setPen(Qt.PenStyle.NoPen)

        # draw rectangle
        rect = QRect(0, 0, self.width(), self.height())



        # cheack if is checked
        if not self.isChecked():
            # raaw bg
            p.setBrush(QColor(self._bg_color))

            # draw border
            p.setPen(QColor(self._border_color))
            border_thickness = 1  # Толщина границы (в пикселях)
            rect = self.rect().adjusted(border_thickness, border_thickness, -border_thickness, -border_thickness)
            p.drawRoundedRect(0, 0, rect.width(), self.height(), self.height() / 2, self.height() / 2)

            # draw circle
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(self._circle_position, 4, 22, 22)
        else:
            # raaw bg
            p.setBrush(QColor(self._active_color))

            # draw border
            p.setPen(QColor(self._border_color))
            border_thickness = 1  # Толщина границы (в пикселях)
            rect = self.rect().adjusted(border_thickness, border_thickness, -border_thickness, -border_thickness)
            p.drawRoundedRect(0, 0, rect.width(), self.height(), self.height() / 2, self.height() / 2)

            # draw circle
            p.setBrush(QColor(self.circle_active_color))
            p.drawEllipse(self.width() - 26, 4, 22, 22)


        #end draw
        p.end()



