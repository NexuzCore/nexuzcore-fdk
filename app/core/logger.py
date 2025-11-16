import logging
import sys
import os



# ===========================================
# BASIC ANSI CONSTANTS
# ===========================================
RESET = "\033[0m"

# ---------- Text Attributes ----------
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
INVERT = "\033[7m"
HIDDEN = "\033[8m"
STRIKETHROUGH = "\033[9m"

# ANSI Farbdefinitionen
NEON_GREEN  = "\033[38;2;57;255;20m"
NEON_CYAN   = "\033[38;2;21;255;255m"
NEON_ORANGE = "\033[38;2;255;140;0m"
NEON_RED    = "\033[38;2;255;50;40m"

# Extra neon tones
NEON_PINK       = "\033[38;2;255;20;147m"
NEON_PURPLE     = "\033[38;2;190;0;255m"
NEON_YELLOW     = "\033[38;2;255;255;20m"
NEON_BLUE       = "\033[38;2;20;150;255m"
NEON_MAGENTA    = "\033[38;2;255;0;255m"

# ===========================================
# 8-COLOR FOREGROUND (STANDARD)
# ===========================================
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# ===========================================
# 8-BRIGHT FOREGROUND
# ===========================================
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# ===========================================
# BACKGROUND COLORS (8-color)
# ===========================================
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"

# ===========================================
# BACKGROUND COLORS (bright)
# ===========================================
BG_BRIGHT_BLACK = "\033[100m"
BG_BRIGHT_RED = "\033[101m"
BG_BRIGHT_GREEN = "\033[102m"
BG_BRIGHT_YELLOW = "\033[103m"
BG_BRIGHT_BLUE = "\033[104m"
BG_BRIGHT_MAGENTA = "\033[105m"
BG_BRIGHT_CYAN = "\033[106m"
BG_BRIGHT_WHITE = "\033[107m"


ICON_START   = "▶️"
ICON_STOP    = "⏹️"
ICON_PAUSE   = "⏸️"
ICON_SUCCESS = "✔"

ICON_INSTALL = "🛠️"


# Custom Formatter für Konsole
class ColorFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: f"{NEON_CYAN}[debug] {BLACK}| {WHITE}Console {BLACK}> {RESET} | %(message)s",
        logging.INFO:  f"{NEON_CYAN}[info] {BLACK}| {WHITE}Console {BLACK}> {RESET} | %(message)s",
        logging.WARNING: f"{NEON_ORANGE}[warning] {BLACK}| {WHITE}Console {BLACK}> {RESET} | %(message)s",
        logging.ERROR: f"{NEON_RED}[error] {BLACK}| {WHITE}Console {BLACK}> {RESET} | %(message)s",
        logging.CRITICAL: f"{NEON_RED}[critical] {BLACK}| {WHITE}Console {BLACK}> {RESET} | %(message)s",
        "INSTALL": f"{NEON_CYAN}[install]{ICON_INSTALL} {BLACK}| {NEON_GREEN}%(message)s",
        "START": f"{NEON_CYAN}[start]{ICON_START} {BLACK}| {NEON_GREEN}%(message)s",
        "STOP": f"{NEON_RED}[stop]{ICON_STOP} {BLACK}| {NEON_BLUE}%(message)s",
        "PAUSE": f"{NEON_YELLOW}[pause]{ICON_PAUSE} {BLACK}| {NEON_PURPLE}%(message)s",
        "SUCCESS": f"{NEON_GREEN}[success]{ICON_SUCCESS} {BLACK}| {NEON_ORANGE}%(message)s"
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, self.FORMATS.get(record.levelname, self.FORMATS[logging.INFO]))
        if getattr(record, "success", False):
            fmt = self.FORMATS["SUCCESS"]
        formatter = logging.Formatter(fmt)
        return formatter.format(record)

# Formatter ohne Farben für Datei
class PlainFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "[debug] | %(message)s",
        logging.INFO: "[info] | %(message)s",
        logging.WARNING: "[warning] | %(message)s",
        logging.ERROR: "[error] | %(message)s",
        logging.CRITICAL: "[critical] | %(message)s",
        "INSTALL": f"[install] | {ICON_INSTALL} | %(message)s",
        "START": f"[start] | {ICON_START}  | %(message)s",
        "STOP": f"[stop] | {ICON_STOP}  | %(message)s",
        "PAUSE": f"[pause] | {ICON_PAUSE}  | %(message)s",
        "SUCCESS": f"[success] | {ICON_SUCCESS}| %(message)s"
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, self.FORMATS.get(record.levelname, self.FORMATS[logging.INFO]))
        if getattr(record, "success", False):
            fmt = self.FORMATS["SUCCESS"]
        if getattr(record, "start", False):
            fmt = self.FORMATS["START"]
        if getattr(record, "stop", False):
            fmt = self.FORMATS["STOP"]
        if getattr(record, "pause", False):
            fmt = self.FORMATS["PAUSE"]
        if getattr(record, "install", False):
            fmt = self.FORMATS["INSTALL"]
        formatter = logging.Formatter(fmt)
        return formatter.format(record)

# Basis-Logger einrichten
logger = logging.getLogger("nexuzcore")
logger.setLevel(logging.DEBUG)

# Konsolen-Handler (bunt)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColorFormatter())

# Datei-Handler (ohne Farben)
logfile_path = os.path.join(os.getcwd(), "nexuzcore-build.log")
file_handler = logging.FileHandler(logfile_path, encoding='utf-8')
file_handler.setFormatter(PlainFormatter())

logger.handlers = [console_handler, file_handler]
logger.propagate = False

# Erfolg als eigenes Level
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

START_LEVEL = 27
logging.addLevelName(START_LEVEL, "START")

STOP_LEVEL = 28
logging.addLevelName(STOP_LEVEL, "STOP")

PAUSE_LEVEL = 29
logging.addLevelName(PAUSE_LEVEL, "PAUSE")

INSTALL_LEVEL = 30
logging.addLevelName(INSTALL_LEVEL, "PAUSE")

def success(msg, *args, **kwargs):
    logger.log(SUCCESS_LEVEL, msg, *args, extra={"success": True}, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)
    
def start(msg, *args, **kwargs):
    logger.log(START_LEVEL, msg, *args, extra={"start": True}, **kwargs)
    
def stop(msg, *args, **kwargs):
    logger.log(STOP_LEVEL, msg, *args, extra={"stop": True}, **kwargs)
    
def pause(msg, *args, **kwargs):
    logger.log(PAUSE_LEVEL, msg, *args, extra={"pause": True}, **kwargs)
    
def install(msg, *args, **kwargs):
    logger.log(INSTALL_LEVEL, msg, *args, extra={"start": True}, **kwargs)

# Für direkten Zugriff
log = logger