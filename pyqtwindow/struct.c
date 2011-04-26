#include <stdio.h>
 
/* Define a type point to be a struct with integer members x, y */
typedef struct {
   int    x;
   int    y;
} point;
 
 
int main(int argc, char * argv[]) {
 
/* Define a variable p of type point, and initialize all its members inline! */
    point p = {1,2};
    point s[2] = {{1,2},{3,4}}; 
/* Define a variable q of type point. Members are initialized with the defaults for their derivative types such as 0. */
    point q;
 
/* Assign the value of p to q, copies the member values from p into q. */
    q = p;
 
/* Change the member x of q to have the value of 2 */
    q.x = 2;
    printf("Array of Points: %d", s[1].x);
/* Demonstrate we have a copy and that they are now different. */
    if (p.x != q.x) printf("The members are not equal! %d != %d", p.x, q.x);
}

