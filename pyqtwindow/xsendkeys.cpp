/* xsendkey.c ************************************************/
/*
 * This file is subject to the terms and conditions of the GNU General Public
 * License.  See the file COPYING in the main directory of this archive for
 * more details.
 * 
 */

#include <stdio.h>
#include <stdlib.h>
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <lineak/lineak_core_functions.h>
#include <lineak/lineak_util_functions.h>
#include <lineak/lobject.h>

#include <vector>
#include <iostream>
#include <stdlib.h>

using namespace std;
using namespace lineak_core_functions;
using namespace lineak_util_functions;

char *ProgramName;

Display *dpy;
int scr;
Window win;
unsigned int width, height;

int main(int argc, char **argv)
{
    Window ret_win;
    int x, y;
    unsigned int border_width, depth;
    int keycode;
    string argument;

    ProgramName = argv[0];
    if (argc < 1)
        return 1;

    argument = string(argv[1]);
    
    dpy = XOpenDisplay("");
    if (!dpy) {
        fprintf(stderr, "%s: Cannot connect to display ...\n", ProgramName);
        return 1;
    }
    scr = DefaultScreen(dpy);
    win = RootWindow(dpy, scr);
    XGetGeometry(dpy, win, &ret_win, &x, &y, &width, &height, &border_width, &depth);
    /////////////////////////////////
    // lineak stuff
    vector<string> args;
    args.push_back(argument);
    vector<string> elements;
    vector<int>codes;
    KeySym mykeysym;
    KeyCode xkeycode;
    
    int index = 0;
    string parsed = "";
    string symname = lineak_util_functions::strip_space(args[0]);
    string smodifiers = "";
    while (symname.find('+') != string::npos) {
            index = symname.find('+');
            smodifiers = symname.substr(index+1,symname.size()-(index+1));
            parsed = symname.substr(0,index);
            symname = smodifiers;
            if ( parsed == "control" || parsed == "Control" || parsed == "CONTROL" )
                    parsed = "Control_L";
            if ( parsed == "shift" || parsed == "Shift" || parsed == "SHIFT" )
                    parsed = "Shift_L";
            if ( parsed == "mod1" || parsed == "alt" || parsed == "Alt" || parsed == "ALT" )
                    parsed = "Alt_L";
            //cout << "element = " << parsed << endl;
            elements.push_back(parsed);
            //cout << "remainder = " << smodifiers << endl;
    }
    elements.push_back(smodifiers);
    //inspect_vector(elements);
    
    for (vector<string>::const_iterator it = elements.begin(); it != elements.end(); it++) {
        mykeysym = XStringToKeysym(it->c_str());
        xkeycode = XKeysymToKeycode(dpy, mykeysym);     
        //cout << *it << " has code of " << (int)xkeycode << endl; 
        codes.push_back((int)xkeycode);
    }
    /*
    cout << "vector has " << codes.size() << " elements: { ";
    for (vector<int>::const_iterator it = codes.begin(); it != codes.end(); it++)
                                    cout << *it << " ";
    cout << "} " << endl;
    */
    for (vector<int>::const_iterator it = codes.begin(); it != codes.end(); it++) {
            keycode = *it;
            XTestFakeKeyEvent(dpy, keycode, 1, 0);
            //cout << "sending key down: " << keycode << endl;
            XSync(dpy, 1);
    }
    vector<int>::const_iterator it = codes.end();
    
    do {
            it--;
            keycode = *it;
            XTestFakeKeyEvent(dpy, keycode, 0, 0);
            //cout << "sending key up: " << keycode << endl;
            XSync(dpy, 1);
    }
    while (it != codes.begin());
            
    return 0;
}
