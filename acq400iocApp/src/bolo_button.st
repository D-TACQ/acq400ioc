/* bolo_button.st
 * activate bolo modes based on front panel button presses
 * */

program bolo_button

/*
 * +r to make the generated code reentrant, 
 * thus allowing more than one instance of the program to run on an IOC.
 */
option +r;

/*
 * +m to include the main procedure (seqMain.c) for a standalone program.
 */
/* option +m; */

%%#include <stdio.h>
%%#include <stdlib.h>

#define MODE_IDLE  0
#define MODE_CALIB 1
#define MODE_RUN   2

/* monitor the event bus alias for HDMI GPIO */
int calib_button; assign calib_button to "{uut}:{site}:SIG:EVT_MB:COUNT";
monitor calib_button;

/* monitor the event bus alias for HDMI SYNC */
int run_button; assign run_button to "{uut}:{site}:SIG:EVT_S2:COUNT";
monitor run_button;


/*
 * run_calibfit is part of the BOLODSP package
 * set_arm is the garden variety way of arming an ACQ400
 * it will then capture on trigger
 *
 * TODO: Put in some logic in case these files do not exist
 * if (file_not_exist) { tell user bolo package not enabled }
 */
string calib_script = "/usr/local/bin/run_calibfit";
string run_script = "/usr/local/bin/set_arm";

int verbose;

/* monitor previous state */
int calib_button0 = 1;
int run_button0 = 1;

int site;
char* message;
int rc;

ss bolo_button_states {
	state init {
		when() {
			if (macValueGet("verbose")){
				verbose = macValueGet("verbose")[0] - '0';
			}
			site = macValueGet("site")[0] - '0';
		} state idle
	}
	
	state idle {
		entry {
			if (verbose){
				printf("in idle state on site %d \n", site);
			}
		}

                when(calib_button > calib_button0) {
                    calib_button0 = calib_button;
                } state calib

                when(run_button > run_button0) {
                    run_button0 = run_button;
                } state run

		/* Reset detection if count decreased */
		when(run_button < run_button0) {
		    if (verbose) {
			printf("run_button reset detected on site %d\n", site);
		    }
		    run_button0 = run_button; 
		} state idle

		when(calib_button < calib_button0) {
		    if (verbose) {
			printf("calib_button reset detected on site %d\n", site);
		    }
		    calib_button0 = calib_button;
		} state idle

		when() {
			
		} state idle
	}

	state calib {
		entry {
			if (verbose){
				printf("in calib state on site %d \n", site);
			}
                        rc = system(calib_script);
		}

		when() {
                    calib_button0 = calib_button;
                    run_button0 = run_button;
		} state idle
	}

	state run {
		entry {
			if (verbose){
				printf("in run state on site %d \n", site);
			}
                        rc = system(run_script);
		}

		when() {
		    calib_button0 = calib_button;
                    run_button0 = run_button;
		} state idle
	}
}
