        
// Sending fake keypress events to an X11 window
// Filed under: Nerd Notes — adam @ 12:43 pm
// 
// This C++ example code will send a cursor-down event to the currently focussed window. It can easily be modified to send other key events. It would be a good starting point to write a virtual keyboard or remote control application.

// Send a fake keystroke event to an X window.
// by Adam Pierce - http://www.doctort.org/adam/
// This is public domain software. It is free to use by anyone for any purpose.

//To compile it, you need to type this:
//g++ -o XFakeKey XFakeKey.cpp -L/usr/X11R6/lib -lX11

#include <X11/Xlib.h>
#include <X11/keysym.h>

// The key code to be sent.
// A full list of available codes can be found in /usr/include/X11/keysymdef.h
#define KEYCODE XK_3

// Function to create a keyboard event
XKeyEvent createKeyEvent(Display *display, Window &win,
                           Window &winRoot, bool press,
                           int keycode, int modifiers)
{
   XKeyEvent event;

   event.display     = display;
   event.window      = win;
   event.root        = winRoot;
   event.subwindow   = None;
   event.time        = CurrentTime;
   event.x           = 1;
   event.y           = 1;
   event.x_root      = 1;
   event.y_root      = 1;
   event.same_screen = True;
   event.keycode     = XKeysymToKeycode(display, keycode);
   event.state       = modifiers;

   if(press)
      event.type = KeyPress;
   else
      event.type = KeyRelease;

   return event;
}

main()
{
// Obtain the X11 display.
   Display *display = XOpenDisplay(0);
   if(display == NULL)
      return -1;

// Get the root window for the current display.
   Window winRoot = XDefaultRootWindow(display);

// Find the window which has the current keyboard focus.
   Window winFocus;
   int    revert;
   XGetInputFocus(display, &winFocus, &revert);

// Send a fake key press event to the window.
   XKeyEvent event = createKeyEvent(display, winRoot, winRoot, true, KEYCODE, Mod1Mask);
   XSendEvent(event.display, event.window, True, KeyPressMask, (XEvent *)&event);

// Send a fake key release event to the window.
//    event = createKeyEvent(display, winFocus, winRoot, false, KEYCODE, 0);
//    XSendEvent(event.display, event.window, True, KeyPressMask, (XEvent *)&event);

// Done.
   XCloseDisplay(display);
   return 0;
}