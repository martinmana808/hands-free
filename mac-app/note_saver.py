import subprocess

class NoteSaver:
    def __init__(self):
        pass
        
    def save_note(self, text: str):
        """
        Takes the transcribed text and creates a new Apple Note with it.
        We use AppleScript to ensure it lands directly in the Notes app.
        """
        if not text:
            return
            
        print(f"Saving to Apple Notes: '{text}'")
        
        # Escape quotes for AppleScript
        safe_text = text.replace('"', '\\"')
        
        applescript = f'''
        tell application "Notes"
            tell account "iCloud"
                if not (exists folder "Notes") then
                    make new folder with properties {{name:"Notes"}}
                end if
                
                -- Create a new note with the given text
                make new note at folder "Notes" with properties {{body:"{safe_text}"}}
            end tell
        end tell
        '''
        
        try:
            # Run the applescript
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                check=True
            )
            print("Note saved successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error saving note: {e}")
            print(f"stderr: {e.stderr}")
