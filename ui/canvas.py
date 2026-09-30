from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtWidgets import QWidget

class ImageCanvas(QWidget):
    crop_committed=Signal(float,float,float,float)
    crop_cancelled=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.image=None; self.before_image=None; self.zoom=1.0; self.offset=QPoint(0,0)
        self.dragging=False; self.last_mouse_position=QPoint(); self.show_before=False
        self.crop_mode=False; self.crop_start=None; self.crop_end=None
        self.setMinimumSize(500,400); self.setMouseTracking(True)

    def set_image(self,image,before_image=None):
        self.image=image; self.before_image=before_image
        if not self.crop_mode:self.fit_image()
        self.update()

    def fit_image(self):
        if self.image is None:return
        width,height=self.width(),self.height(); iw,ih=self.image.width,self.image.height
        if not iw or not ih:return
        self.zoom=min(width/iw,height/ih)*.95; self.offset=QPoint(width//2,height//2)

    def image_rect(self):
        if self.image is None:return QRect()
        w=int(self.image.width*self.zoom); h=int(self.image.height*self.zoom)
        return QRect(self.offset.x()-w//2,self.offset.y()-h//2,w,h)

    def zoom_in(self):self.zoom=min(20.0,self.zoom*1.2);self.update()
    def zoom_out(self):self.zoom=max(.02,self.zoom/1.2);self.update()
    def reset_view(self):self.fit_image();self.update()
    def toggle_before(self):self.show_before=not self.show_before;self.update()

    def start_crop(self):
        if self.image is None:return
        self.crop_mode=True; self.crop_start=None; self.crop_end=None
        self.setCursor(Qt.CrossCursor); self.update()

    def cancel_crop(self):
        self.crop_mode=False;self.crop_start=None;self.crop_end=None;self.setCursor(Qt.ArrowCursor);self.crop_cancelled.emit();self.update()

    def _clamp_to_image(self,p):
        r=self.image_rect()
        return QPoint(max(r.left(),min(r.right(),p.x())),max(r.top(),min(r.bottom(),p.y())))

    def _crop_values(self):
        if self.image is None or self.crop_start is None or self.crop_end is None:return None
        r=self.image_rect()
        x1=max(r.left(),min(self.crop_start.x(),self.crop_end.x())); x2=min(r.right(),max(self.crop_start.x(),self.crop_end.x()))
        y1=max(r.top(),min(self.crop_start.y(),self.crop_end.y())); y2=min(r.bottom(),max(self.crop_start.y(),self.crop_end.y()))
        if x2-x1<5 or y2-y1<5:return None
        return ((x1-r.left())/max(r.width(),1),(y1-r.top())/max(r.height(),1),(x2-r.left())/max(r.width(),1),(y2-r.top())/max(r.height(),1))

    def wheelEvent(self,event):
        if self.image is None:return
        self.zoom*=1.15 if event.angleDelta().y()>0 else 1/1.15
        self.zoom=max(.02,min(20.0,self.zoom));self.update()

    def mousePressEvent(self,event):
        if self.crop_mode and event.button()==Qt.LeftButton:
            p=self._clamp_to_image(event.position().toPoint()); self.crop_start=p;self.crop_end=p;self.update();return
        if event.button()==Qt.MiddleButton:
            self.dragging=True;self.last_mouse_position=event.position().toPoint();self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self,event):
        if self.crop_mode and self.crop_start is not None and event.buttons()&Qt.LeftButton:
            self.crop_end=self._clamp_to_image(event.position().toPoint());self.update();return
        if not self.dragging:return
        current=event.position().toPoint();self.offset+=current-self.last_mouse_position;self.last_mouse_position=current;self.update()

    def mouseReleaseEvent(self,event):
        if self.crop_mode and event.button()==Qt.LeftButton and self.crop_start is not None:
            self.crop_end=self._clamp_to_image(event.position().toPoint());values=self._crop_values()
            if values:self.crop_committed.emit(*values)
            self.crop_mode=False;self.crop_start=None;self.crop_end=None;self.setCursor(Qt.ArrowCursor);self.update();return
        if event.button()==Qt.MiddleButton:
            self.dragging=False;self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape and self.crop_mode:self.cancel_crop();return
        super().keyPressEvent(event)

    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),Qt.black)
        if self.image is None:
            painter.setPen(Qt.white);painter.drawText(self.rect(),Qt.AlignCenter,"Open an image to begin");return
        image=self.before_image if self.show_before and self.before_image is not None else self.image
        pixmap=QPixmap.fromImage(ImageQt(image)); rect=self.image_rect()
        scaled=pixmap.scaled(rect.width(),rect.height(),Qt.KeepAspectRatio,Qt.SmoothTransformation)
        painter.drawPixmap(rect.left(),rect.top(),scaled)
        if self.crop_mode:
            r=self.image_rect(); painter.fillRect(r,QColor(0,0,0,90))
            if self.crop_start is not None and self.crop_end is not None:
                x=min(self.crop_start.x(),self.crop_end.x()); y=min(self.crop_start.y(),self.crop_end.y())
                w=abs(self.crop_start.x()-self.crop_end.x()); h=abs(self.crop_start.y()-self.crop_end.y())
                painter.setCompositionMode(QPainter.CompositionMode_Clear); painter.fillRect(QRect(x,y,w,h),Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver); painter.setPen(QPen(Qt.white,2));painter.drawRect(QRect(x,y,w,h))
                painter.setPen(QPen(QColor(255,255,255,150),1))
                for i in (1,2):
                    painter.drawLine(x+w*i/3,y,x+w*i/3,y+h);painter.drawLine(x,y+h*i/3,x+w,y+h*i/3)
