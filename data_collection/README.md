# Fruit Ninja Data Collector
The following code snippets are used to modify this website: https://poki.com/en/g/fruit-ninja 

The modified website can generate raw images and automatically download them to your device.
Every image downloaded will have a name of `[Frame number]-[Sequence number]-[Class name].png` and will have transparency. The frame number is just an incrementing number to distinguish between frames. The sequence number is the order in which these objects were rendered in (which is necessary to separate the classes from each other later to create the mask). The class name is the name of the object that was rendered in that sequence.

# Website Modifications
First, go into your chrome settings and search for `Download`. Change the download location to where you want the raw dataset images to be saved on your computer. Make sure that location has enough storage space because a new image will be downloaded every 500ms. You need to also disable `Ask where to save each file before downloading` otherwise it will ask you every 500ms where to save the new frame. (You can restore your chrome settings to normal once you're done collecting data).

When you're done with step one, go to https://poki.com/en/g/fruit-ninja and open the inspect tab or developer tools, and paste the following into the console and press enter:
```js
window.saveFrame = false;   // Trigger a frame save
window.saveFullFrame = false;   // Trigger a frame save
window.frameNumber = 0;     // Current frame number
window.seq = 0;
window.recordSample = false;// Record a dataset sample (frame + classes)

// Save current content of the canvas
window.doSaveFrame = function(gl) {
    //console.log("Saving frame!");
    var width = gl.canvas.width;
    var height = gl.canvas.height;
    var pixels = new Uint8Array(4 * width * height); // 4 bytes per pixel (RGBA)

    // Read the pixels from the WebGL framebuffer
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

    // Create an image from the pixel data
    var imageData = new ImageData(new Uint8ClampedArray(pixels), width, height);

    // Create a temporary canvas to convert the image data to a base64 PNG
    var tempCanvas = document.createElement("canvas");
    var tempCtx = tempCanvas.getContext("2d");
    tempCanvas.width = width;
    tempCanvas.height = height;

    // Put the image data on the temporary canvas
    tempCtx.putImageData(imageData, 0, 0);

    // Convert the canvas to a base64-encoded PNG
    var imageUrl = tempCanvas.toDataURL("image/png");

    // Create a download link and trigger a download
    var link = document.createElement("a");
    link.href = imageUrl;
    link.download = window.frameName;
    link.click();

    link.remove();
    tempCanvas.remove();
}
```
---
After that, go to the `sources` tab and press `CTRL + P` and search for a file named `three.module.js`. That file has a function named `render` (You can find it by `CTRL + F` and search for `gl.drawArrays( mode, start, count );` or you can scroll to line `14326`). After that, place a breakpoint in the function and it should break at that breakpoint and pause in debugger. While it's paused, go back to the console and paste this code to replace the render function:
```js
// The render function that's actually called when an object is rendered
this.render = function( start, count ) {

		gl.drawArrays( mode, start, count );
        if (window.saveFrame) {
            window.saveFrame = false;
            window.doSaveFrame(gl);
            window.gl = gl;
        }
		info.update( count, mode, 1 );

	}
```
---
Now the render function will save what it just rendered if `window.saveFrame` is set to true. Next, we need to replace the function that's using the render function and actually rendering the objects. We only want to save objects that are out of interest (fruits and bombs). Go to the sources tab again and back to the same file `three.module.js` and remove your old breakpoint. Search for `if ( opaqueObjects.length > 0 ) renderObjects` (it should be on the line `23959`). Set a new breakpoint there and resume the debugger and it should pause again on this new line (this is necessary because the context needs to change). When that is done, paste this in the console to replace the `renderObjects` function:
```js
// The function that renders the objects one by one
renderObjects = function( renderList, scene, camera ) {

		const overrideMaterial = scene.isScene === true ? scene.overrideMaterial : null;

        const index26 = renderList.findIndex(item => item.id === 26);
        if (index26 !== -1) {
            const [item26] = renderList.splice(index26, 1); // Remove the item with id 26
            renderList.unshift(item26); // Add it to the start of the list
        }

		for ( let i = 0, l = renderList.length; i < l; i ++ ) {
			const renderItem = renderList[ i ];

			const object = renderItem.object;
			const geometry = renderItem.geometry;
			const material = overrideMaterial === null ? renderItem.material : overrideMaterial;
			const group = renderItem.group;

            if (renderItem.id == 26){
                material.map = null;
                material.color.set(0xFFB6C1);
                material.needsUpdate = true;
            }

			if ( camera.isArrayCamera ) {

				const cameras = camera.cameras;

				for ( let j = 0, jl = cameras.length; j < jl; j ++ ) {

					const camera2 = cameras[ j ];

					if ( object.layers.test( camera2.layers ) ) {

						state.viewport( _currentViewport.copy( camera2.viewport ) );

						currentRenderState.setupLightsView( camera2 );

						renderObject( object, scene, camera2, geometry, material, group );

					}

				}

			} else {
                if (renderItem.object.name && renderItem.object.name.length > 3 && window.recordSample) {
                    window.saveFrame = true;
                    window.frameName = window.frameNumber + "-" + window.seq + "-" + renderItem.object.name;
                    window.seq++;
                }
                renderObject( object, scene, camera, geometry, material, group );
			}

		}
        if(window.recordSample){
            window.saveFullFrame = true;
        }
	}
```
---
Once you remove your breakpoint and let the debugger resume, you will notice that the background will have turned dark pink. This is necessary to segment out the fruits and bombs later. Now we also need to save the effects frame (fruit splashes and the slashes of your mouse) and for that, we must go to another file called `phaser.js` and search for `renderer.postRender();` (Line `159437`) and again place a breakpoint on that line, and it should pause there in debugger. After that, paste this in console:
```js
renderer.postRender = function ()
    {
        if (this.contextLost) { return; }

        this.flush();

        this.emit(Events.POST_RENDER);

        var state = this.snapshotState;

        if (state.callback)
        {
            WebGLSnapshot(this.canvas, state);

            state.callback = null;
        }

        if (this.textureFlush > 0)
        {
            this.startActiveTexture++;
            this.currentActiveTexture = 1;
        }

        const phasercanv = document.querySelector("#enable3d-phaser-canvas");
        const mainCanv = document.querySelector("#enable3d-three-canvas")
        if (phasercanv && window.saveFullFrame) {
            window.saveFullFrame = false;
            window.frameName = window.frameNumber + "-x-EntireFrame";
            window.recordSample = false;

            const imageURL = phasercanv.toDataURL("image/png");
            const downloadLink = document.createElement('a');
            downloadLink.href = imageURL;
            downloadLink.download =  window.frameName;
            downloadLink.click();

            window.frameNumber++;
            window.seq = 0;
        }
        if (mainCanv && window.saveFullFrame) {
            window.frameName = window.frameNumber + "-x-EntireFrameAgain";
            const imageURL = mainCanv.toDataURL("image/png");
            const downloadLink = document.createElement('a');
            downloadLink.href = imageURL;
            downloadLink.download =  window.frameName;
            downloadLink.click();
        }
    }
```
With this, all necessary modifications should be done.
# Data generation
To start actually collection data, you can paste this in console anything and it will start:
```js
// Start recording dataset samples at regular interval
window.recording = setInterval(() => {
    window.recordSample = true;
}, 500);	//Once every 500th ms
```
And to stop recording, paste this in console:
```js
clearInterval(recording);
```
However, this is a bad way to do it because it will also save the main screen, the loading screen and everything else that is not wanted, this will make it hard to sort out the data later and make it very noisy. To avoid this, we should make it save data when we are playing and stop when we are not. To do this, we need to access the main scene that has current game state. 

To do this, go to the file named `mainScene.js` and search for `update(time,delta) {` (line `1181`). This function is called repeatedly, we want to set a breakpoint there to pause the debugger there. After that happens, paste this in console:
```js
window.mainS = this
```
This means that now we have exposed the main scene as gloabl variable called `mainS`. With that, we can check if the gameState is 2 (which means playing). Paste this in terminal: (Make sure to clearInterval from previous step if you have set it)
```js
setInterval(() => {
    if(window.mainS.gameState == 2){
        window.recordSample = true;
    }
}, 500);
```
Now, it should automatically save images while you're playing and stop on game over. However, it doesn't stop immediantly, it saves a couple of extra frames on game over that aren't necessary. In order to make the dataset less noisy, everytime you lose in the game, go to the dataset and manually delete the last few frames.